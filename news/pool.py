from __future__ import annotations

from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import asyncio

import os
import sqlite3
import trafilatura
import types
from typing import Final, Optional, Union, Protocol, Any, Tuple
import logging

def process_html(html):
    return trafilatura.extract(html, output_format='txt', include_images=True, include_formatting=True,
                        include_tables=True, include_comments=False, favor_recall=True)

LOGGER = logging.getLogger("pool")

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

@dataclass(frozen=True)
class ArticleParagraphs:
    article_id: int
    paragraphs: list[tuple[int, str]]
    topics: list[str]
    topics_map: dict[int, str]
    paragraph_ratings: dict[int, list[tuple[int, str, bool]]]
    summary: str
    summary_rating: dict[int, float]
    title: str = ""

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

    async def fetch_article(self, url: str) -> tuple[str, str]:
        async with self._lock:
            result = self._get_article(url)
            if result:
                return result

            LOGGER.info(f"[ArticleRepository] Downloading article for {url}")
            title, raw_html = await PlaywrightPool.fetch_html(url)
            processed_html = process_html(raw_html)

            # Upsert:
            self._conn.execute(
                f"""
                        INSERT INTO articles (url, title, raw_html, processed_html)
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

    async def get_article(self, url: str) -> tuple[str, str] | None:
        async with self._lock:
            return self._get_article(url)

    def _get_article(self, url: str) -> tuple[str, str] | None:
        # Single writer at a time when using sqlite3 – avoids `database is locked`
        row = self._row_for_url(url)

        if row:  # row = (id, url, title, raw, processed)
            LOGGER.info(f"[ArticleRepository] Found cached article for {url}")
            return row[2], row[4]  # processed_html already present

        LOGGER.info(f"[ArticleRepository] Article was not found for {url}")
        return None

    async def has_paragraphs(self, url) -> bool:
        async with self._lock:
            row = self._row_for_url(url)
            if not row:
                return False

            cur = self._conn.cursor()
            row = cur.execute(f"SELECT COUNT(*) FROM summaries WHERE article_id = {row[0]}")

            result = row.fetchone()
            if not result or result[0] == 0:
                return False
            return True

    async def get_latest_articles(self, count, last = -1) -> list[tuple[int, str, str, str]] | None:
        async with self._lock:
            cur = self._conn.cursor()
            if last > 0:
                row = cur.execute(f"SELECT id, url, title, processed_html FROM articles WHERE id < {self.cursor_type} ORDER BY id DESC LIMIT {self.cursor_type}", (last, count))
            else:
                row = cur.execute(
                    f"SELECT id, url, title, processed_html FROM articles ORDER BY id DESC LIMIT {self.cursor_type}",
                    (count,))

            return row.fetchall()

    async def get_paragraphs(self, article_url : str) -> ArticleParagraphs | None:
        async with self._lock:
            cur = self._conn.cursor()
            row = cur.execute(f"SELECT id, title FROM articles WHERE url = {self.cursor_type}", (article_url,))
            article_id, title = row.fetchone()

            if article_id is None:
                return None

            row = cur.execute(f"SELECT id, paragraph_text FROM paragraphs WHERE article_id = {self.cursor_type}", (article_id,))

            paragraphs: list[tuple[int, str]] = row.fetchall()

            row = cur.execute(f"SELECT id, topic_text FROM topics WHERE article_id = {self.cursor_type}", (article_id,))

            topics: list[tuple[int, str]] = row.fetchall()

            topics_map = {}
            for topic in topics:
                topics_map[topic[0]] = topic[1]

            row = cur.execute(f"SELECT paragraph_id, topic_id, rating FROM topic_ratings WHERE topic_id IN (SELECT id FROM topics WHERE article_id = {self.cursor_type})", (article_id, ))

            topic_ratings: list[tuple[int, int, bool]] = row.fetchall()

            topic_ratings_map = {}
            for paragraph_id, topic_id, rating in topic_ratings:
                if not paragraph_id in topic_ratings_map:
                    topic_ratings_map[paragraph_id] = []
                topic_ratings_map[paragraph_id].append((topic_id, topics_map[topic_id], rating))

            row = cur.execute(f"SELECT summary_text FROM summaries WHERE article_id = {self.cursor_type}", (article_id,))

            summary = row.fetchone()[0]

            row = cur.execute(f"SELECT paragraph_id, rating FROM summary_ratings WHERE article_id = {self.cursor_type}", (article_id,))

            summary_ratings = row.fetchall()

            summary_ratings_map = {}
            for paragraph_id, rating in summary_ratings:
                summary_ratings_map[paragraph_id] = rating

            return ArticleParagraphs(
                article_id=article_id,
                paragraphs=paragraphs,
                topics=[topic[1] for topic in topics],
                topics_map=topics_map,
                paragraph_ratings=topic_ratings_map,
                summary=summary,
                summary_rating=summary_ratings_map,
                title=title
            )

    async def set_paragraphs(self, url, paragraphs, summary, summary_ratings, topics, topic_ratings):
        async with self._lock:
            article_id = self._row_for_url(url)[0]

            cur = self._conn.cursor()

            rows = cur.execute(f"""
                INSERT INTO summaries (article_id, summary_text) 
                VALUES ({self.cursor_type}, {self.cursor_type})
                ON CONFLICT(article_id) DO UPDATE SET
                summary_text=EXCLUDED.summary_text
                RETURNING article_id;
            """, (article_id, summary))

            summary_id = rows.fetchone()[0]

            topic_ids = []
            for topic in topics:
                rows = cur.execute(f"""
                    INSERT INTO topics (article_id, topic_text) 
                    VALUES ({self.cursor_type}, {self.cursor_type})
                    RETURNING id;
                """, (article_id, topic))
                topic_ids.append(rows.fetchone()[0])

            for paragraph, summary_rating, gel in zip(paragraphs, summary_ratings, topic_ratings):
                rows = cur.execute(f"""
                    INSERT INTO paragraphs (article_id, paragraph_text) 
                    VALUES ({self.cursor_type}, {self.cursor_type})
                    RETURNING id;
                """, (article_id, paragraph))

                paragraph_id = rows.fetchone()[0]

                cur.execute(f"""
                    INSERT INTO summary_ratings (paragraph_id, article_id, rating) VALUES ({self.cursor_type}, {self.cursor_type}, {self.cursor_type}) 
                """, (paragraph_id, summary_id, float(summary_rating)))

                for topic_id, rating in zip(topic_ids, gel):
                    self._conn.execute(f"""
                        INSERT INTO topic_ratings (paragraph_id, topic_id, rating) 
                        VALUES ({self.cursor_type}, {self.cursor_type}, {self.cursor_type})
                    """, (paragraph_id, topic_id, rating))

            self._conn.commit()



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
            CREATE TABLE IF NOT EXISTS articles (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                url            TEXT UNIQUE NOT NULL,
                title          TEXT NOT NULL,
                raw_html       TEXT NOT NULL,
                processed_html TEXT NOT NULL
            )
            """
        )
        self._conn.execute("""CREATE TABLE IF NOT EXISTS paragraphs (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id     INTEGER NOT NULL,
                paragraph_text TEXT NOT NULL,
                foreign key (article_id) references articles(id)
            )
            """)
        self._conn.execute("""CREATE TABLE IF NOT EXISTS topics (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id     INTEGER NOT NULL,
                topic_text     TEXT NOT NULL,
                foreign key (article_id) references articles(id)
            )
            """)
        self._conn.execute("""CREATE TABLE IF NOT EXISTS topic_ratings (
                paragraph_id   INTEGER,
                topic_id       INTEGER NOT NULL,
                rating         BOOLEAN NOT NULL,
                primary key (paragraph_id, topic_id),
                foreign key (paragraph_id) references paragraphs(id),
                foreign key (topic_id) references topics(id)
            )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS summaries (
                article_id   INTEGER PRIMARY KEY,
                summary_text TEXT NOT NULL,
                foreign key (article_id) references articles(id)
            )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS summary_ratings (
                paragraph_id   INTEGER NOT NULL,
                article_id     INTEGER NOT NULL,
                rating         FLOAT NOT NULL,
                primary key (paragraph_id, article_id),
                foreign key (paragraph_id) references paragraphs(id),
                foreign key (article_id) references articles(id)           
            )""")
        self._conn.commit()

    def _row_for_url(self, url: str) -> Optional[Tuple[Any, ...]]:
        cur = self._conn.cursor()
        cur.execute(f"SELECT id, url, title, raw_html, processed_html FROM articles WHERE url = {self.cursor_type}", (url,))
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