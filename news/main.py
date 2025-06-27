from __future__ import annotations

import asyncio
import logging
import os
from typing import Final, Optional, List

import discord
from dotenv import load_dotenv
import re
from pool import PlaywrightPool, ArticleRepository
import trafilatura
import io

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

load_dotenv()

DISCORD_TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")

ROLE_NAME = "Newsulizer"

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)

LOGGER = logging.getLogger("main")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

article_repository = ArticleRepository()

async def send_text_file(channel: discord.abc.Messageable, content: str, filename: str = "article.md") -> None:
    fp = io.BytesIO(content.encode("utf-8"))
    file = discord.File(fp, filename=filename)
    await channel.send("📄 Full article attached:", file=file)


async def handle_article_url(message: discord.Message, url: str) -> None:
    """
    Placeholder: download + analyse the article here.

    Currently just acknowledges receipt so you can verify the event flow.
    """
    LOGGER.info("Received URL from %s: %s", message.author, url)

    try:
        processed_html = await article_repository.get_article(url)
        # TODO: parse `html`, summarise, etc.
        await message.channel.send(f"✅ Article downloaded – {len(processed_html):,} bytes.")
        await send_text_file(message.channel, processed_html)
    except:
        LOGGER.exception("Playwright failed")
        await message.channel.send("❌ Sorry, I couldn't fetch that page.")


def extract_first_url(text: str) -> Optional[str]:
    """Return the first http(s)://… substring found in *text*, or None."""

    match = re.search(r"https?://\S+", text)
    return match.group(0) if match else None

@bot.event
async def on_ready() -> None:
    LOGGER.info("Logged in as %s (id=%s)", bot.user, bot.user.id)
    await PlaywrightPool.start()
    LOGGER.info("Playwright pool ready")
    LOGGER.info("------")

@bot.event
async def on_message(message: discord.Message) -> None:
    # Ignore our own messages
    if message.author == bot.user:
        return

    is_dm = message.guild is None

    overwrite = False
    if not is_dm:
        role = discord.utils.get(message.guild.roles, name=ROLE_NAME)
        if role is None:
            # The role doesn't even exist in this server
            await message.channel.send(f"Warning! Role **{ROLE_NAME}** not found in this server.")
            return

        overwrite = role in message.channel.overwrites

    # Either a DM or a channel message that mentions the bot

    is_mention = (bot.user in message.mentions if message.guild else False) or overwrite

    if not (is_dm or is_mention):
        return

    url = extract_first_url(message.content)
    if not url:
        await message.channel.send("Please send me a link to a news article.")
        return

    await message.channel.send(f"🔗 Thanks, <@{message.author.id}>! I’ve queued that article for analysis.")

    # Launch the processing task without blocking Discord’s event loop
    asyncio.create_task(handle_article_url(message, url))

def main() -> None:
    if DISCORD_TOKEN is None:
        raise RuntimeError("Set the DISCORD_TOKEN environment variable or add it to a .env file.")

    try:
        bot.run(DISCORD_TOKEN)
    finally:
        asyncio.run(PlaywrightPool.stop())

if __name__ == "__main__":
    main()
