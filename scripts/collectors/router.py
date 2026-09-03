REQUIRED_SOURCE_KEYS = {"name", "url", "county", "default_city"}


def validate_source(source: dict) -> list[str]:
    return [
        f"missing source key: {key}"
        for key in sorted(REQUIRED_SOURCE_KEYS - set(source))
    ]


def collector_name(source: dict) -> str:
    return str(source.get("collector") or "jsonld")
