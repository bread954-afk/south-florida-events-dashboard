from pathlib import Path


def test_workflow_runs_tests_playwright_and_validation():
    text = Path('.github/workflows/update-events.yml').read_text(encoding='utf-8')
    required = [
        'python -m playwright install --with-deps chromium',
        'python -m pytest -q',
        'python -m scripts.update_events',
        'python -m scripts.validate_events broward-events.json miami-events.json',
        'workflow_dispatch',
        'contents: write',
    ]
    for token in required:
        assert token in text


def test_workflow_commits_last_updated_metadata():
    from pathlib import Path
    text = Path('.github/workflows/update-events.yml').read_text(encoding='utf-8')
    assert 'last-updated.json' in text
