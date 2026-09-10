import re
from collections import Counter
from urllib.parse import urlsplit


def _norm(value: str) -> str:
    return re.sub(r"\W+", "", str(value or "").lower())


_STATUS_WORDS = re.compile(r"\b(cancelled|canceled|postponed|rescheduled)\b", re.I)


def canonical_url(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parts = urlsplit(text)
    path = parts.path.rstrip("/") or "/"
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{path}"


def name_identity(value: str) -> str:
    return _norm(_STATUS_WORDS.sub("", str(value or "")))


def _event_specific_url(value: str) -> bool:
    text = canonical_url(value)
    if not text:
        return False
    path = urlsplit(text).path.rstrip("/")
    return path not in {"", "/events", "/calendar"}


_TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?\b", re.I)


def _norm_start_time(value: str) -> str:
    text = str(value or "").strip()
    match = _TIME_RE.search(text)
    if not match:
        return _norm(text)
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3).lower()
    return f"{hour:02d}:{minute:02d}{meridiem}m"


def event_key(event: dict) -> tuple[str, str, str, str]:
    return (
        str(event.get("date", "")),
        _norm(event.get("name", "")),
        _norm(event.get("venue", "")),
        _norm_start_time(event.get("time", "")),
    )


def _prefer_time(current: str, incoming: str) -> str:
    current = str(current or "")
    incoming = str(incoming or "")
    if not incoming:
        return current
    if current.strip().lower() in {"", "tbd", "night", "day", "evening"}:
        return incoming
    if ("-" in incoming or "–" in incoming) and not ("-" in current or "–" in current):
        return incoming
    return current


def _merge_fields(current: dict, incoming: dict, material: bool = False) -> dict:
    if material:
        for field in ("date", "name", "venue", "city"):
            value = incoming.get(field)
            if value not in (None, ""):
                current[field] = value
        current["time"] = incoming.get("time") or current.get("time", "")
    else:
        current["time"] = _prefer_time(current.get("time", ""), incoming.get("time", ""))

    for field in ("url", "cost", "source", "city", "venue", "category", "age"):
        value = incoming.get(field)
        if value not in (None, "", "Check source"):
            current[field] = value

    current["featured"] = bool(current.get("featured") or incoming.get("featured"))
    current["new"] = False
    return current


def merge_events(existing: list[dict], discovered: list[dict]) -> list[dict]:
    out = {event_key(e): dict(e) for e in existing}
    url_counts = Counter(
        canonical_url(e.get("url")) for e in existing if canonical_url(e.get("url"))
    )

    for event in discovered:
        key = event_key(event)
        if key in out:
            out[key] = _merge_fields(out[key], event)
            continue

        incoming_url = canonical_url(event.get("url"))
        material_key = None
        if incoming_url and _event_specific_url(incoming_url) and url_counts[incoming_url] == 1:
            for old_key, current in out.items():
                if (
                    canonical_url(current.get("url")) == incoming_url
                    and name_identity(current.get("name")) == name_identity(event.get("name"))
                ):
                    material_key = old_key
                    break

        if material_key is not None:
            current = out.pop(material_key)
            current = _merge_fields(current, event, material=True)
            out[event_key(current)] = current
            continue

        out[key] = dict(event)

    return sorted(
        out.values(),
        key=lambda e: (
            e.get("date", ""), e.get("time", ""), e.get("name", ""), e.get("venue", "")
        ),
    )
