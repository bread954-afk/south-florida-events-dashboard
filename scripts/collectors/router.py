REQUIRED_SOURCE_KEYS = {"name", "url", "county", "default_city"}

ARENA_COLLECTORS = {
    "hardrock_hollywood", "amerant", "broward_center", "kaseya",
    "hard_rock_stadium", "arsht", "jlkc", "miami_beach_bandshell",
}

NIGHTLIFE_COLLECTORS = {
    "hardrock_nightlife", "liv", "eleven", "club_space", "factory_town",
    "zeyzey", "kemistry", "backyard", "tin_roof",
}

COMEDY_MUSIC_COLLECTORS = {
    "miami_improv", "dania_improv", "revolution_live", "culture_room", "gulfstream",
}

MUNICIPAL_COLLECTORS = {
    "hollywood_calendar", "sunrise_calendar", "fort_lauderdale_calendar",
    "visit_lauderdale", "miami_beach_calendar", "wynwood", "doral_calendar",
    "coral_gables_calendar", "miami_worldcenter", "frost_science",
}

PLATFORM_COLLECTORS = {
    "ticketmaster", "eventbrite", "dice", "resident_advisor", "shotgun", "posh",
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
    if name in COMEDY_MUSIC_COLLECTORS:
        return "comedy_music"
    if name in MUNICIPAL_COLLECTORS:
        return "municipal"
    if name in PLATFORM_COLLECTORS:
        return "platform"
    return "jsonld"
