"""Bounded public HTTP retrieval, immutable content versions, and an audit log."""

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


SECRET_NAMES = {"apikey", "api_key", "key", "token", "access_token", "authorization", "signature", "sig"}
USER_AGENT_ENV = "MEF_USER_AGENT"


def load_fixture(replay):
    """Read an explicit synthetic HTTP fixture. A replay never falls back to live requests."""
    if replay is None:
        return None
    try:
        fixture = json.loads(Path(replay).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{replay} is not valid JSON ({error.msg}); nothing was fetched") from None
    if (
        not isinstance(fixture, dict)
        or fixture.get("mode") != "synthetic"
        or not fixture.get("as_of")
        or not isinstance(fixture.get("responses"), dict)
    ):
        raise ValueError(f"{replay} is not a synthetic replay fixture with as_of and responses; nothing was fetched")
    return fixture


def resolve_user_agent(value=None, live=True):
    """Live requests identify the person running them; offline replays never reach the network."""
    agent = (value or os.environ.get(USER_AGENT_ENV) or "").strip()
    if not live:
        return agent or "mef (offline replay)"
    if (
        not agent
        or re.search(r"(?i)your[_ -]|example\.(?:com|org|net)|\.(?:invalid|example|localhost)\b|[<>]", agent)
        or not re.search(r"@|https?://", agent)
    ):
        raise ValueError(
            f"Live requests need your own contact: set {USER_AGENT_ENV} or --user-agent, "
            "for example 'mef (<your email or URL>)'"
        )
    return agent


def is_wrapped_pdf(body, content_type):
    """Recognize a PDF inside an issuer's SerialBlob response, without deserializing Java."""
    return (
        "pdf" in content_type.lower()
        and body.startswith(b"\xac\xed\x00\x05")
        and b"javax.sql.rowset.serial.SerialBlob" in body[:150]
        and 0 < body[:1024].find(b"%PDF-") < 1024
        and b"%%EOF" in body[-1024:]
    )


def safe_url(url):
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("Only ordinary public HTTP(S) URLs are supported")
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in SECRET_NAMES]
    return urlunsplit((p.scheme, p.netloc.lower(), p.path, urlencode(query), ""))


UMASK = os.umask(0)
os.umask(UMASK)


def write_atomic(path, body):
    """Write bytes through a fresh temporary file and a rename, so a reader never sees a half-written file even when
    parallel agents share 1 folder."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as f:
            f.write(body)
        os.chmod(name, 0o666 & ~UMASK)  # mkstemp makes the file private; the result should be like any other
        Path(name).replace(path)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def save_json(path, value):
    write_atomic(path, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def save_extraction(directory, source_id, value):
    """Keep cited text versions immutable across re-fetches of the same URL."""
    content = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    relative = Path("extracted") / (source_id + "-" + digest + ".json")
    path = Path(directory) / relative
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError("Existing extraction content does not match its hash")
    else:
        save_json(path, value)
    return {"extracted_path": str(relative), "extracted_sha256": digest}


class Fetcher:
    def __init__(self, directory, user_agent, transport="curl", max_requests=45, min_interval=0.6, refresh=False):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.user_agent = user_agent
        self.transport = transport
        self.max_requests = max_requests
        self.min_interval = min_interval
        self.refresh = refresh
        self.requests = 0
        self.last_request = 0.0
        self.audit = []

    def _request(self, url):
        if self.requests >= self.max_requests:
            raise RuntimeError("Run request budget exhausted")
        time.sleep(max(0, self.min_interval - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        self.requests += 1
        if self.transport == "urllib":
            try:
                with urlopen(Request(url, headers={"User-Agent": self.user_agent}), timeout=25) as r:
                    body = r.read(20_000_001)
                    return r.status, dict(r.headers), r.url, body
            except HTTPError as e:
                return e.code, dict(e.headers), e.url, b""
        # curl uses its system trust store. TLS verification remains enabled.
        with tempfile.TemporaryDirectory() as td:
            body_path, header_path = Path(td) / "body", Path(td) / "headers"
            proc = subprocess.run(
                [
                    "curl",
                    "-sS",
                    "-L",
                    "--max-redirs",
                    "5",
                    "--max-time",
                    "25",
                    "--max-filesize",
                    "20000000",
                    "--proto",
                    "=http,https",
                    "--proto-redir",
                    "=http,https",
                    "--user-agent",
                    self.user_agent,
                    "-D",
                    str(header_path),
                    "-o",
                    str(body_path),
                    "-w",
                    "%{http_code}\n%{url_effective}",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode:
                raise OSError(f"curl failed ({proc.returncode}); check network and TLS trust")
            status, final_url = proc.stdout.split("\n", 1)
            blocks = re.split(r"\r?\n\r?\n", header_path.read_text(errors="replace").strip())
            headers = {}
            for line in blocks[-1].splitlines()[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.lower()] = v.strip()
            return int(status), headers, final_url, body_path.read_bytes()

    def fetch(self, url, source_type="document", discovered_from=None):
        url = safe_url(url)
        key = hashlib.sha256(url.encode()).hexdigest()[:20]
        index = self.directory / "index" / (key + ".json")
        if index.exists() and not self.refresh:
            saved = json.loads(index.read_text())
            if (saved["status"] == "ok" and (self.directory / saved["local_path"]).exists()) or saved["status"] in {
                "blocked",
                "not_found",
            }:
                saved["cache_hit"] = True
                self.audit.append(saved)
                return saved
        now = datetime.now(timezone.utc).isoformat()
        result = {
            "source_id": key,
            "original_url": url,
            "source_type": source_type,
            "discovered_from": safe_url(discovered_from) if discovered_from else None,
            "requested_at": now,
            "retrieved_at": now,
            "cache_hit": False,
            "status": "unknown",
        }
        try:
            for attempt in range(2):
                code, headers, final, body = self._request(url)
                headers = {k.lower(): v for k, v in headers.items()}
                if code not in {429, 500, 502, 503, 504} or attempt == 1:
                    break
                wait = headers.get("retry-after", "2")
                # Date-form Retry-After and long backoffs remain explicit retry exhaustion.
                if not wait.isdigit() or int(wait) > 10:
                    break
                time.sleep(max(1, int(wait)))
            result.update(
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                http_status=code,
                final_url=safe_url(final),
                content_type=headers.get("content-type", ""),
                etag=headers.get("etag"),
                last_modified=headers.get("last-modified"),
            )
            if code != 200:
                result["status"] = "blocked" if code in {401, 403} else "not_found" if code == 404 else "http_error"
            elif len(body) > 20_000_000:
                result["status"] = "size_limit"
            elif not (
                "html" in result["content_type"].lower()
                or "json" in result["content_type"].lower()
                or "csv" in result["content_type"].lower()
                or "xml" in result["content_type"].lower()
                or body.startswith(b"%PDF")
                or is_wrapped_pdf(body, result["content_type"])
                or (body.startswith(b"PK") and "presentationml.presentation" in result["content_type"].lower())
            ):
                result["status"] = "unsupported_content"
            else:
                digest = hashlib.sha256(body).hexdigest()
                kind = (
                    "json"
                    if "json" in result["content_type"]
                    else "csv"
                    if "csv" in result["content_type"].lower()
                    else "pdf"
                    if body.startswith(b"%PDF") or is_wrapped_pdf(body, result["content_type"])
                    else "pptx"
                    if body.startswith(b"PK")
                    else "xml"
                    if "xml" in result["content_type"].lower()
                    else "html"
                )
                relative = Path("documents") / (key + "-" + digest[:12] + "." + kind)
                path = self.directory / relative
                path.parent.mkdir(exist_ok=True)
                write_atomic(path, body)
                result.update(status="ok", sha256=digest, bytes=len(body), local_path=str(relative))
                if is_wrapped_pdf(body, result["content_type"]):
                    result["content_wrapper"] = "java_serial_blob_pdf_preserved_as_received"
        except (OSError, URLError, RuntimeError, subprocess.TimeoutExpired, ValueError) as e:
            result.update(status="fetch_error", error=f"{type(e).__name__}: {str(e)[:140]}")
        save_json(index, result)
        self.audit.append(result)
        return result

    def text(self, source):
        if source["status"] != "ok":
            raise ValueError("Source is unavailable")
        return (self.directory / source["local_path"]).read_text(encoding="utf-8", errors="replace")


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("A dated observation needs an ISO timestamp with a timezone")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Use an ISO timestamp with a timezone") from None
    if result.tzinfo is None:
        raise ValueError("Use an ISO timestamp with a timezone")
    return result.astimezone(timezone.utc)


class ReplayFetcher(Fetcher):
    """Run the identical collector on explicit synthetic HTTP fixtures."""

    def __init__(self, directory, fixture):
        super().__init__(directory, "synthetic-offline-replay", refresh=True, min_interval=0, max_requests=250)
        self.fixture = fixture

    def _request(self, url):
        if self.requests >= self.max_requests:
            raise RuntimeError("Replay request budget exhausted")
        self.requests += 1
        response = self.fixture["responses"].get(url)
        if response is None:
            return 404, {"content-type": "application/json"}, url, b"[]"
        body = response.get("body", "")
        if response.get("base64"):
            body = base64.b64decode(response["base64"])
        elif not isinstance(body, str):
            body = json.dumps(body).encode()
        else:
            body = body.encode()
        return (
            response.get("status", 200),
            {"content-type": response.get("content_type", "application/json")},
            url,
            body,
        )

    def fetch(self, *args, **kwargs):
        result = super().fetch(*args, **kwargs)
        result["retrieved_at"] = self.fixture["as_of"]
        save_json(self.directory / "index" / (result["source_id"] + ".json"), result)
        return result
