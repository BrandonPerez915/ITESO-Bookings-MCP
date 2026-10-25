from __future__ import annotations

from typing import Optional
from playwright.async_api import async_playwright, BrowserContext, Page

from src.config import USER_DATA_DIR, SPORTS_BOOKINGS_URL

_playwright_instance = None
_context: BrowserContext | None = None

async def get_browser_context(headless: bool = True) -> BrowserContext:
    """
    Retrieves or creates a persistent browser context on disk.
    This ensures that once a user completes MFA login for ITESO SSO,
    the authenticated session remains active across all ITESO platforms.
    """
    global _playwright_instance, _context

    if _context is None:
        _playwright_instance = await async_playwright().start()
        _context = await _playwright_instance.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1280, "height": 800},
        )
    return _context


async def close_browser_context() -> None:
    """Closes the browser context and Playwright instance to release resources."""
    global _playwright_instance, _context
    if _context:
        try:
            await _context.close()
        except Exception:
            pass
        _context = None
    if _playwright_instance:
        try:
            await _playwright_instance.stop()
        except Exception:
            pass
        _playwright_instance = None


async def open_page(url: str, headless: bool = True) -> Page:
    """Opens a new tab navigating to the specified URL."""
    context = await get_browser_context(headless=headless)
    page = await context.new_page()
    await page.goto(url, wait_until="domcontentloaded")
    return page


async def open_bookings_page(
    url: str,
    headless: bool = True,
) -> Page:
    """
    Opens a new tab navigating to a booking portal URL.
    Defaults to the sports booking portal if no URL is provided.
    """
    return await open_page(url, headless=headless)
