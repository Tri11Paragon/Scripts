from __future__ import annotations

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import asyncio

import os
import sqlite3
import trafilatura
import types
from typing import Final, Optional, Union, Protocol, Any, Tuple
import logging

def process_html(html):
    return trafilatura.extract(html, output_format='markdown', include_images=True, include_formatting=True,
                        include_tables=True, include_comments=False, favor_recall=True)

LOGGER = logging.getLogger("pool")
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
# )

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
    async def fetch_html(cls, url: str) -> tuple[str, str]:
        if cls._browser is None:
            await cls.start()

        async with cls._sema:                       # throttle concurrency
            page: Page = await cls._ctx.new_page()
            try:
                await page.goto(url, wait_until="load", timeout=60_000)
                html = await page.content()
                title = await page.title()
                return title, html
            finally:
                await page.close()

class DBConnectionInfo:
    def __init__(
            self,
            dbname: str,
            user: str,
            password: str,
            host: str = "localhost",
            port: int = 5432,
    ) -> None:
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password


class ArticleRepository:
    """
    A very small wrapper around a database that maintains a single table
    called 'articles' inside a database called 'newsulizer'.

    • If you pass an existing DB-API connection, it will be used as-is.
    • If you don’t pass anything, a local SQLite file called
      './newsulizer.sqlite3' is created/used automatically.
    """

    _CREATE_DB_SQLITE = "newsulizer.sqlite3"
    _TABLE_NAME = "articles"

    def __init__(
        self,
        connection_info: Optional[DBConnectionInfo] = None,
        sqlite_path: Optional[str] = None,
    ) -> None:
        """
        Parameters
        ----------
        sqlite_path:
            Path to an SQLite file.  Defaults to ./newsulizer.sqlite3
            when *connection* is omitted.
        """

        if connection_info is None:
            sqlite_path = sqlite_path or self._CREATE_DB_SQLITE
            connection = self._make_sqlite_conn(sqlite_path)
            self.cursor_type = "?"
        else:
            connection = self._make_postgres_conn(
                host=connection_info.host,
                port=connection_info.port,
                dbname=connection_info.dbname,
                user=connection_info.user,
                password=connection_info.password,
            )
            self.cursor_type = "%s"

        self._conn = connection
        self._ensure_schema()

        # Protect SQLite (which is not async-safe) by one lock
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    async def get_article(self, url: str) -> tuple[str, str]:
        """
        Main entry point.
        • Returns the processed text if it is already cached.
        • Otherwise downloads it, processes it, stores it, and returns it.
        """

        # Single writer at a time when using sqlite3 – avoids `database is locked`
        async with self._lock:
            row = self._row_for_url(url)

            if row:                          # row = (id, url, title, raw, processed)
                LOGGER.info(f"[ArticleRepository] Found cached article for {url}")
                return row[2], row[4]                           # processed_html already present

        LOGGER.info(f"[ArticleRepository] Downloading article for {url}")
        title, raw_html = await PlaywrightPool.fetch_html(url)
        processed_html = process_html(raw_html)

        async with self._lock:
            # Upsert:
            self._conn.execute(
                f"""
                INSERT INTO {self._TABLE_NAME} (url, title, raw_html, processed_html)
                VALUES ({self.cursor_type}, {self.cursor_type}, {self.cursor_type}, {self.cursor_type})
                ON CONFLICT(url) DO UPDATE SET
                    title=EXCLUDED.title,
                    raw_html=EXCLUDED.raw_html,
                    processed_html=EXCLUDED.processed_html
                """,
                (url, title, raw_html, processed_html),
            )
            self._conn.commit()

        return title, processed_html

    def close(self) -> None:
        """Close the underlying DB connection."""
        try:
            self._conn.close()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #
    def _ensure_schema(self) -> None:
        """Create the articles table if it does not yet exist."""
        # Simple feature detection for DBs that do not support
        # `ON CONFLICT` (mainly older MySQL) could be added here.
        self._conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._TABLE_NAME} (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                url            TEXT UNIQUE NOT NULL,
                title          TEXT NOT NULL,
                raw_html       TEXT NOT NULL,
                processed_html TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def _row_for_url(self, url: str) -> Optional[Tuple[Any, ...]]:
        cur = self._conn.cursor()
        cur.execute(f"SELECT id, url, title, raw_html, processed_html FROM {self._TABLE_NAME} WHERE url = {self.cursor_type}", (url,))
        return cur.fetchone()

    @staticmethod
    def _make_sqlite_conn(sqlite_path: str) -> sqlite3.Connection:
        first_time = not os.path.exists(sqlite_path)
        connection = sqlite3.connect(sqlite_path, check_same_thread=False)
        # Enforce basic integrity
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")

        if first_time:
            # Ensure a human-readable filename, not an unnamed ATTACH
            LOGGER.info(f"[ArticleRepository] Created fresh local database at '{sqlite_path}'")
        else:
            LOGGER.info(f"[ArticleRepository] Reusing existing local database at '{sqlite_path}'")
        return connection

    @staticmethod
    def _make_postgres_conn(*, host: str, port: int, dbname: str, user: str, password: Optional[str]):
        try:
            import psycopg2
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "psycopg2 is required for PostgreSQL support – "
                "run `pip install psycopg2-binary`"
            ) from exc

        conn = psycopg2.connect(
            host=host, port=port, dbname=dbname, user=user, password=password
        )
        conn.autocommit = False
        return conn