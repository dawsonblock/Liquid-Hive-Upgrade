from __future__ import annotations

import time
from typing import Any, Optional

from playwright.async_api import async_playwright

from .normalizer import html_to_text
from .schemas import PageContent


def _detect_challenge(html: str) -> str:
    h = (html or "").lower()
    if "captcha" in h or "are you human" in h or "bot detection" in h:
        return "challenge_detected"
    return "none"


async def fetch_playwright(
    url: str,
    wait_state: str = "networkidle",
    wait_selector: Optional[str] = None,
    storage_state_path: Optional[str] = None,
) -> PageContent:
    t0 = time.time()
    network_payloads: list[dict[str, Any]] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = (
            await browser.new_context(storage_state=storage_state_path)
            if storage_state_path
            else await browser.new_context()
        )
        page = await ctx.new_page()

        def on_response(response):
            try:
                if "application/json" in (response.headers.get("content-type", "")):
                    network_payloads.append(
                        {
                            "url": response.url,
                            "status": response.status,
                            "headers": dict(response.headers),
                        }
                    )
            except Exception:
                pass

        page.on("response", on_response)

        await page.goto(url, timeout=20000)
        await page.wait_for_load_state(wait_state)
        if wait_selector:
            try:
                await page.wait_for_selector(wait_selector, timeout=5000)
            except Exception:
                pass
        html = await page.content()
        png = await page.screenshot(full_page=True)
        title, text = html_to_text(html)
        await ctx.close()
        await browser.close()
    challenge_status = _detect_challenge(html)
    blocked = challenge_status != "none"
    dt = int((time.time() - t0) * 1000)
    return PageContent(
        url=url,
        status=200,
        title=title,
        mime="text/html",
        content=text,
        content_html=html,
        screenshot_png=png,
        network_payloads=network_payloads,
        fetched_at=time.time(),
        captcha_required=blocked,
        blocked=blocked,
        headers={},
        rendered=True,
        elapsed_ms=dt,
        challenge_status=challenge_status,
    )
