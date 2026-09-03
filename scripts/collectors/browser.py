from scripts.collectors.base import CollectorResult


def browser_enabled_for(source: dict) -> bool:
    return source.get("browser_fallback") is True


def render_html(url: str, wait_selector: str | None = None, timeout_ms: int = 30000) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if wait_selector:
                page.wait_for_selector(wait_selector, timeout=timeout_ms)
            else:
                try:
                    page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 12000))
                except Exception:
                    pass
            return page.content()
        finally:
            browser.close()
