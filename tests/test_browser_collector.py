from scripts.collectors.browser import browser_enabled_for


def test_browser_fallback_must_be_explicit():
    assert browser_enabled_for({"browser_fallback": True}) is True
    assert browser_enabled_for({"browser_fallback": False}) is False
    assert browser_enabled_for({}) is False
