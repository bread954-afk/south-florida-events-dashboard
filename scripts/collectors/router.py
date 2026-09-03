REQUIRED_SOURCE_KEYS = {"name", "url", "county", "default_city"}

ARENA_COLLECTORS = {
    "hardrock_hollywood", "amerant", "broward_center", "kaseya",
    "hard_rock_stadium", "arsht", "jlkc", "miami_beach_bandshell",
}

NIGHTLIFE_COLLECTORS = {
    "hardrock_nightlife", "liv", "eleven", "club_space", "factory_town",
    "zeyzey", "kemistry", "backyard", "tin_roof",
}


def validate_source(source: dict) -> list[str]:
    return [
        f"missing source key: {key}"
        for key in sorted(REQUIRED_SOURCE_KEYS - set(source))
    ]


def collector_name(source: dict) -> str:
    return str(source.get("collector") or "jsonld")


def collector_group(name: str) -> str:
    if name in ARENA_COLLECTORS:
        return "arena"
    if name in NIGHTLIFE_COLLECTORS:
        return "nightlife"
    return "jsonld"
