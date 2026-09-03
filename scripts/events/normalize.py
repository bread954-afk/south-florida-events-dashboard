from datetime import datetime
from urllib.parse import urljoin

from dateutil import parser as dtparse


def parse_datetime(value) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return dtparse.parse(str(value))
    except (ValueError, TypeError, OverflowError):
        return None


def format_time(value: datetime) -> str:
    hour = value.strftime("%I").lstrip("0") or "12"
    return f"{hour}:{value.strftime('%M')} {value.strftime('%p')}"


def normalize_event(raw: dict, source: dict, page_url: str) -> dict | None:
    name = str(raw.get("name") or "").strip()
    start = parse_datetime(raw.get("start") or raw.get("startDate"))
    if not name or start is None:
        return None

    url = str(raw.get("url") or page_url)
    if not url.startswith(("http://", "https://")):
        url = urljoin(page_url, url)

    return {
        "date": start.strftime("%Y-%m-%d"),
        "time": str(raw.get("time") or format_time(start)),
        "name": name,
        "venue": str(raw.get("venue") or source["name"]).strip(),
        "city": str(raw.get("city") or source.get("default_city", "")).strip(),
        "category": str(raw.get("category") or "Event").strip(),
        "cost": str(raw.get("cost") or "Check source").strip(),
        "url": url,
        "source": str(raw.get("source") or source["name"]).strip(),
        "age": str(raw.get("age") or "").strip(),
        "featured": bool(raw.get("featured", False)),
        "new": bool(raw.get("new", True)),
    }
