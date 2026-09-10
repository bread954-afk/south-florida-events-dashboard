import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.collectors.router import collect_source
from scripts.events.merge import merge_events
from scripts.events.validate import validate_dataset


ROOT = Path(__file__).resolve().parents[1]
TRACKING_YEAR = 2026
TRACKING_START_MONTH = 9
TRACKING_END_MONTH = 12
EASTERN = ZoneInfo("America/New_York")


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def current_eastern_time() -> datetime:
    return datetime.now(EASTERN)


def tracked_months(now: datetime) -> list[tuple[int, int]]:
    stamp = now if now.tzinfo else now.replace(tzinfo=EASTERN)
    stamp = stamp.astimezone(EASTERN)
    if stamp.year > TRACKING_YEAR:
        return []
    if stamp.year < TRACKING_YEAR:
        start = TRACKING_START_MONTH
    else:
        start = max(TRACKING_START_MONTH, stamp.month)
    if start > TRACKING_END_MONTH:
        return []
    return [(TRACKING_YEAR, month) for month in range(start, TRACKING_END_MONTH + 1)]


def county_label(county: str) -> str:
    return "Broward" if county == "broward" else "Miami"


def write_last_updated(root: Path = ROOT, now: datetime | None = None) -> dict:
    stamp = now or current_eastern_time()
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=EASTERN)
    else:
        stamp = stamp.astimezone(EASTERN)
    payload = {"updated_at": stamp.isoformat(timespec="seconds")}
    (root / "last-updated.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def update_county_months(
    county: str,
    sources: list[dict],
    months: list[tuple[int, int]],
    root: Path = ROOT,
) -> tuple[int, int, list[str]]:
    filename = "broward-events.json" if county == "broward" else "miami-events.json"
    path = root / filename
    existing = load_json(path, [])
    discovered = []
    warnings = []
    label = county_label(county)

    for year, month in months:
        month_key = f"{year:04d}-{month:02d}"
        for source in sources:
            prefix = f"{label} {month_key} / {source['name']}"
            if source.get("enabled", True) is False:
                print(f"[SKIP] {prefix}: disabled")
                continue

            result = collect_source(source, year, month)
            if result.status == "ok":
                if source.get("warn_on_empty") and not result.events:
                    line = f"{prefix}: ok but returned 0 events"
                    warnings.append(line)
                    print(f"[WARN] {line}")
                else:
                    print(f"[OK] {prefix}: {len(result.events)} events")
                discovered.extend(result.events)
            elif result.status == "disabled":
                print(f"[SKIP] {prefix}: disabled")
            else:
                line = f"{prefix}: {result.status}: {result.message}"
                warnings.append(line)
                print(f"[WARN] {line}")

    merged = merge_events(existing, discovered)
    errors = validate_dataset(merged, previous_count=len(existing))
    if errors:
        raise RuntimeError("; ".join(errors))

    path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(existing), len(merged), warnings


def update_county(
    county: str,
    sources: list[dict],
    year: int,
    month: int,
    root: Path = ROOT,
) -> tuple[int, int, list[str]]:
    return update_county_months(county, sources, [(year, month)], root)


def main() -> int:
    registry = load_json(ROOT / "sources.json", {})
    now = current_eastern_time()
    months = tracked_months(now)

    if months:
        month_text = ",".join(f"{year:04d}-{month:02d}" for year, month in months)
        for county in ("broward", "miami"):
            before, after, warnings = update_county_months(
                county,
                registry.get(county, []),
                months,
                ROOT,
            )
            print(
                f"[DONE] {county}: {before} -> {after}; "
                f"months={month_text}; warnings={len(warnings)}"
            )
    else:
        print("[DONE] no supported discovery months remain after 2026-12")

    metadata = write_last_updated(ROOT, now=now)
    print(f"[DONE] last updated: {metadata['updated_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
