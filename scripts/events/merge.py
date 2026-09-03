import re


def _norm(value: str) -> str:
    return re.sub(r"\W+", "", str(value or "").lower())


def event_key(event: dict) -> tuple[str, str, str, str]:
    return (
        str(event.get("date", "")),
        _norm(event.get("name", "")),
        _norm(event.get("venue", "")),
        str(event.get("time", "")),
    )


def merge_events(existing: list[dict], discovered: list[dict]) -> list[dict]:
    out = {event_key(e): dict(e) for e in existing}

    for event in discovered:
        key = event_key(event)
        if key not in out:
            out[key] = dict(event)
            continue

        current = out[key]
        for field in ("url", "cost", "source", "city", "venue", "category", "age"):
            incoming = event.get(field)
            if incoming not in (None, "", "Check source"):
                current[field] = incoming

        current["featured"] = bool(current.get("featured") or event.get("featured"))
        current["new"] = False

    return sorted(
        out.values(),
        key=lambda e: (
            e.get("date", ""),
            e.get("time", ""),
            e.get("name", ""),
            e.get("venue", ""),
        ),
    )
