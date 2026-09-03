from datetime import datetime

REQUIRED_KEYS = {
    "date", "time", "name", "venue", "city", "category",
    "cost", "url", "source", "age", "featured", "new",
}


def validate_event(event: dict) -> list[str]:
    errors = []
    missing = REQUIRED_KEYS - set(event)
    if missing:
        errors.append(f"missing required keys: {sorted(missing)}")

    try:
        datetime.strptime(str(event.get("date")), "%Y-%m-%d")
    except ValueError:
        errors.append(f"date must use YYYY-MM-DD: {event.get('date')!r}")

    if not str(event.get("name", "")).strip():
        errors.append("name must not be empty")
    if not str(event.get("venue", "")).strip():
        errors.append("venue must not be empty")
    return errors


def validate_dataset(events: list[dict], previous_count: int | None = None) -> list[str]:
    if not isinstance(events, list):
        return ["dataset must be a list"]

    errors = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"event {index} is not an object")
            continue
        for error in validate_event(event):
            errors.append(f"event {index}: {error}")

    if previous_count and previous_count >= 20 and len(events) < previous_count * 0.5:
        errors.append(
            f"suspicious count drop: previous={previous_count}, current={len(events)}"
        )
    return errors
