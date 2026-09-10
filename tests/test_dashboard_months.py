from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MONTHS_JS = ROOT / "dashboard-months.js"


def run_node(expression: str):
    script = f"""
const months = require({json.dumps(str(MONTHS_JS))});
const result = {expression};
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(completed.stdout)


def test_supported_months_are_sep_through_dec_2026():
    assert run_node("months.SUPPORTED_MONTHS") == [
        "2026-09", "2026-10", "2026-11", "2026-12"
    ]


def test_default_month_uses_current_month_and_clamps_outside_range():
    assert run_node("months.defaultMonth(new Date(2026, 8, 10))") == "2026-09"
    assert run_node("months.defaultMonth(new Date(2026, 9, 10))") == "2026-10"
    assert run_node("months.defaultMonth(new Date(2026, 10, 10))") == "2026-11"
    assert run_node("months.defaultMonth(new Date(2026, 11, 10))") == "2026-12"
    assert run_node("months.defaultMonth(new Date(2026, 5, 10))") == "2026-09"
    assert run_node("months.defaultMonth(new Date(2027, 0, 10))") == "2026-12"


def test_month_geometry_is_dynamic():
    assert run_node("months.monthMeta('2026-09')") == {
        "key": "2026-09", "label": "September 2026", "year": 2026,
        "monthIndex": 8, "days": 30, "firstWeekday": 2,
    }
    assert run_node("months.monthMeta('2026-10')") == {
        "key": "2026-10", "label": "October 2026", "year": 2026,
        "monthIndex": 9, "days": 31, "firstWeekday": 4,
    }
    assert run_node("months.monthMeta('2026-11')") == {
        "key": "2026-11", "label": "November 2026", "year": 2026,
        "monthIndex": 10, "days": 30, "firstWeekday": 0,
    }
    assert run_node("months.monthMeta('2026-12')") == {
        "key": "2026-12", "label": "December 2026", "year": 2026,
        "monthIndex": 11, "days": 31, "firstWeekday": 2,
    }


def test_event_month_and_current_month_checks_use_full_year_month():
    assert run_node("months.eventInMonth('2026-10-31','2026-10')") is True
    assert run_node("months.eventInMonth('2026-09-30','2026-10')") is False
    assert run_node("months.sameMonth(new Date(2026, 9, 3),'2026-10')") is True
    assert run_node("months.sameMonth(new Date(2026, 8, 30),'2026-10')") is False


def test_current_week_is_sunday_through_saturday_and_weekend_is_fri_to_sun():
    assert run_node("months.currentWeekDateKeys(new Date(2026, 8, 10))") == [
        "2026-09-06", "2026-09-07", "2026-09-08", "2026-09-09",
        "2026-09-10", "2026-09-11", "2026-09-12",
    ]
    assert run_node("months.currentWeekendDateKeys(new Date(2026, 8, 10))") == [
        "2026-09-11", "2026-09-12", "2026-09-13"
    ]
