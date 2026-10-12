"""Bounded Massive access checks; credentials stay in curl stdin, not URLs."""

import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.parse import quote, urlsplit

from .fetching import Fetcher, save_json


class MassiveFetcher(Fetcher):
    def __init__(self, directory, user_agent, api_key, **kwargs):
        super().__init__(directory, user_agent, refresh=True, **kwargs)
        self.api_key = api_key
        self.provider_message = None

    def fetch(self, *args, **kwargs):
        self.provider_message = None
        result = super().fetch(*args, **kwargs)
        if self.provider_message and result.get("http_status", 0) >= 400:
            result["provider_message"] = self.provider_message
            save_json(self.directory / "index" / (result["source_id"] + ".json"), result)
        return result

    def _request(self, url):
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.hostname != "api.massive.com" or parts.username or parts.password:
            raise ValueError("Massive credentials can only be sent to the documented Massive HTTPS host")
        if self.requests >= self.max_requests:
            raise RuntimeError("Massive request budget exhausted")
        time.sleep(max(0, self.min_interval - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        self.requests += 1

        def config_value(value):
            return value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "").replace("\n", "")

        config = (
            'url = "' + config_value(url) + '"\nheader = "Authorization: Bearer ' + config_value(self.api_key) + '"\n'
        )
        with tempfile.TemporaryDirectory() as td:
            body_path, header_path = Path(td) / "body", Path(td) / "headers"
            response = subprocess.run(
                [
                    "curl",
                    "-q",
                    "--config",
                    "-",
                    "-sS",
                    "--max-time",
                    "25",
                    "--max-filesize",
                    "20000000",
                    "--proto",
                    "=https",
                    "--user-agent",
                    self.user_agent,
                    "-o",
                    str(body_path),
                    "-D",
                    str(header_path),
                    "-w",
                    "%{http_code}",
                    "--header",
                    "Accept: application/json",
                ],
                input=config,
                text=True,
                capture_output=True,
                timeout=30,
            )
            if response.returncode:
                raise OSError(f"curl failed ({response.returncode}); check network and TLS trust")

            def redact(value):
                for secret in {self.api_key, quote(self.api_key, safe="")}:
                    value = value.replace(secret, "[redacted]")
                return value

            body = body_path.read_bytes()
            # Pagination and branding URLs can echo keys; sanitize cached responses.
            for secret in {self.api_key.encode(), quote(self.api_key, safe="").encode()}:
                body = body.replace(secret, b"[redacted]")
            code = int(response.stdout)
            if code >= 400:
                try:
                    data = json.loads(body)
                    note = data.get("message", data.get("error", data.get("status", "Provider access error")))
                except (ValueError, AttributeError):
                    note = body.decode(errors="replace")
                self.provider_message = redact(str(note))[:500]
            blocks = re.split(r"\r?\n\r?\n", header_path.read_text(errors="replace").strip())
            headers = {}
            for line in blocks[-1].splitlines()[1:]:
                if ":" in line:
                    name, value = line.split(":", 1)
                    headers[name.lower()] = redact(value.strip())
            return code, headers, url, body
