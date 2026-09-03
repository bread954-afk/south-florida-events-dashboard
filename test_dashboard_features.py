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


def test_both_dashboards_have_mobile_topbar_and_bottom_navigation():
    for filename in ("broward.html", "miami.html"):
        html = read_dashboard(filename)
        assert 'class="mobile-topbar"' in html
        assert 'id="lastUpdatedMobile"' in html
        assert 'class="mobile-nav"' in html
        assert 'class="mobile-mode active" data-mode="all"' in html
        assert 'class="mobile-mode" data-mode="week"' in html
        assert 'class="mobile-mode" data-mode="favorites"' in html


def test_mobile_css_uses_touch_friendly_responsive_layout():
    for filename in ("broward.html", "miami.html"):
        html = read_dashboard(filename)
        assert '@media(max-width:650px)' in html
        assert '.mobile-topbar{display:flex' in html
        assert '.mobile-nav{display:grid' in html
        assert '.toolbar{position:static' in html
        assert '.fav-btn{width:44px;min-height:44px' in html
        assert '.btn{width:100%;justify-content:center' in html


def test_mobile_and_desktop_mode_controls_stay_in_sync():
    for filename in ("broward.html", "miami.html"):
        html = read_dashboard(filename)
        assert "document.querySelectorAll('.chip,.mobile-mode')" in html
        assert "syncModeControls()" in html
        assert "lastUpdatedMobile" in html
