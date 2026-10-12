"""Shared helpers for public sources: address checks, source records and publication dates."""

from datetime import datetime
import ipaddress
from urllib.parse import urlsplit

from .fetching import safe_url


def public_url(url, synthetic=False):
    url = safe_url(url)
    host = urlsplit(url).hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal")):
        raise ValueError("Company collection requires a public website")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("Private/local addresses cannot be collected")
    if host.endswith(".invalid") and not synthetic:
        raise ValueError("Synthetic website cannot be used for live collection")
    return url


def source_entry(record, title, mode, instrument_id=None, published_at=None):
    value = {
        "id": record["source_id"],
        "title": title,
        "url": record.get("final_url", record["original_url"]),
        "observed_at": record["retrieved_at"],
        "mode": mode,
        "sha256": record.get("sha256"),
        "source_type": record["source_type"],
        "status": record["status"],
        "local_path": record.get("local_path"),
    }
    if instrument_id:
        value["instrument_id"] = instrument_id
    if published_at:
        value["published_at"] = published_at
    return value


def publication(page):
    for node in page.root.descendants("meta"):
        if node.attrs.get("property", node.attrs.get("name", "")).lower() in {
            "article:published_time",
            "datepublished",
            "date",
        }:
            value = node.attrs.get("content", "")
            try:
                when = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if when.tzinfo is not None:
                    return when.isoformat()
            except ValueError:
                pass
    return None
