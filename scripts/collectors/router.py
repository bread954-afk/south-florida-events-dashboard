from scripts.collectors.base import CollectorResult
from scripts.collectors.jsonld import collect_jsonld
from scripts.collectors.arenas import collect_arena
from scripts.collectors.nightlife import collect_nightlife
from scripts.collectors.comedy_music import collect_comedy_music
from scripts.collectors.municipal import collect_municipal
from scripts.collectors.platforms import collect_platform


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

KNOWN_COLLECTORS = (
    ARENA_COLLECTORS
    | NIGHTLIFE_COLLECTORS
    | COMEDY_MUSIC_COLLECTORS
    | MUNICIPAL_COLLECTORS
    | PLATFORM_COLLECTORS
    | {"jsonld"}
)


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
    if name == "jsonld":
        return "jsonld"
    return "unknown"


def collect_source(source: dict, year: int, month: int) -> CollectorResult:
    errors = validate_source(source)
    if errors:
        return CollectorResult(status="config_error", message="; ".join(errors))

    if source.get("enabled", True) is False:
        return CollectorResult(status="disabled", message="source disabled")

    name = collector_name(source)
    if name not in KNOWN_COLLECTORS:
        return CollectorResult(
            status="config_error",
            message=f"unknown collector: {name}",
        )

    try:
        group = collector_group(name)
        if group == "arena":
            return collect_arena(source, year, month)
        if group == "nightlife":
            return collect_nightlife(source, year, month)
        if group == "comedy_music":
            return collect_comedy_music(source, year, month)
        if group == "municipal":
            return collect_municipal(source, year, month)
        if group == "platform":
            return collect_platform(source, year, month)
        return collect_jsonld(source, year, month)
    except Exception as exc:
        return CollectorResult(status="parser_error", message=str(exc))
