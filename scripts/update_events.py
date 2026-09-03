import json
from datetime import datetime
from pathlib import Path

from scripts.collectors.router import collect_source
from scripts.events.merge import merge_events
from scripts.events.validate import validate_dataset


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def update_county(
    county: str,
    sources: list[dict],
    year: int,
    month: int,
    root: Path = ROOT,
) -> tuple[int, int, list[str]]:
    filename = "broward-events.json" if county == "broward" else "miami-events.json"
    path = root / filename
    existing = load_json(path, [])
    discovered = []
    warnings = []

    for source in sources:
        if source.get("enabled", True) is False:
            print(f"[SKIP] {source['name']}: disabled")
            continue

        result = collect_source(source, year, month)
        if result.status == "ok":
            print(f"[OK] {source['name']}: {len(result.events)} events")
            discovered.extend(result.events)
        elif result.status == "disabled":
            print(f"[SKIP] {source['name']}: disabled")
        else:
            line = f"{source['name']}: {result.status}: {result.message}"
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


def main() -> int:
    registry = load_json(ROOT / "sources.json", {})
    now = datetime.now()

    for county in ("broward", "miami"):
        before, after, warnings = update_county(
            county,
            registry.get(county, []),
            now.year,
            now.month,
            ROOT,
        )
        print(f"[DONE] {county}: {before} -> {after}; warnings={len(warnings)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
