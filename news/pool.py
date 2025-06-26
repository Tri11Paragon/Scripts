from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from typing import Final, Optional
import asyncio

class PlaywrightPool:
    _pw = None           # playwright instance
    _browser: Optional[Browser] = None
    _ctx: Optional[BrowserContext] = None
    _sema: asyncio.Semaphore  # limit parallel pages

    @classmethod
    async def start(cls, max_concurrency: int = 4) -> None:
        if cls._pw is not None:
            return

        cls._pw = await async_playwright().start()
        cls._browser = await cls._pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        cls._ctx = await cls._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        cls._sema = asyncio.Semaphore(max_concurrency)

    @classmethod
    async def new_context(cls) -> None:
        if cls._ctx:
            await cls._ctx.close()
        cls._ctx = await cls._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )

    @classmethod
    async def stop(cls) -> None:
        if cls._ctx:
            await cls._ctx.close()
        if cls._browser:
            await cls._browser.close()
        if cls._pw:
            await cls._pw.stop()

    @classmethod
    async def fetch_html(cls, url: str) -> str:
        if cls._browser is None:
            await cls.start()

        async with cls._sema:                       # throttle concurrency
            page: Page = await cls._ctx.new_page()
            try:
                await page.goto(url, wait_until="load", timeout=60_000)
                html = await page.content()
                return html
            finally:
                await page.close()