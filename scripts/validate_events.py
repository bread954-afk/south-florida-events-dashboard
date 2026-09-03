import json
import sys
from pathlib import Path

from scripts.events.validate import validate_dataset


def main(paths: list[str]) -> int:
    failed = False
    for raw_path in paths:
        path = Path(raw_path)
        events = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_dataset(events)
        if errors:
            failed = True
            print(f"[FAIL] {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"[OK] {path}: {len(events)} events")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
