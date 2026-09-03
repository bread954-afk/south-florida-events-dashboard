from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_dashboard(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_both_dashboards_have_home_favorites_and_last_updated_ui():
    for filename in ("broward.html", "miami.html"):
        html = read_dashboard(filename)
        assert 'href="index.html"' in html
        assert 'id="lastUpdated"' in html
        assert 'data-mode="favorites"' in html
        assert 'class="fav-btn' in html
        assert 'localStorage' in html
        assert 'last-updated.json' in html


def test_favorites_use_county_specific_storage_keys():
    broward = read_dashboard("broward.html")
    miami = read_dashboard("miami.html")
    assert 'sf-events-favorites-broward-v1' in broward
    assert 'sf-events-favorites-miami-v1' in miami


def test_favorite_filter_is_implemented_in_mode_filter():
    for filename in ("broward.html", "miami.html"):
        html = read_dashboard(filename)
        assert "mode==='favorites'" in html
        assert "isFavorite(e)" in html
