from __future__ import annotations

import asyncio
import logging
import os
from typing import Final, Optional, List

import discord
from dotenv import load_dotenv
import re
from pool import PlaywrightPool, ArticleRepository
import io
from ollama import chat
from ollama import ChatResponse
from ollama import Client
from ollama import AsyncClient

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

async def send_chat(messages, fmt):
    return await AsyncClient(host="192.168.69.3:11434").chat(
        # model="deepseek-r1:1.5b",
        model="gemma3:12b-it-qat",
        messages=messages,
        stream=False,
        options={
            'temperature': 0.5,
            # "num_ctx": 128000
        },
        think=False)

async def send_text_file(channel: discord.abc.Messageable, content: str, message: str = "📄 Full article attached:", filename: str = "article.md") -> None:
    fp = io.BytesIO(content.encode("utf-8"))
    file = discord.File(fp, filename=filename)
    await channel.send(message, file=file)


async def handle_article_url(message: discord.Message, url: str) -> None:
    """
    Placeholder: download + analyse the article here.

    Currently just acknowledges receipt so you can verify the event flow.
    """
    LOGGER.info("Received URL from %s: %s", message.author, url)

    try:
        title, processed_html = await article_repository.get_article(url)
        paragraphs = processed_html.split("\n")
        paragraphs = [f"\"Paragraph ({i + 1})\": {paragraph.strip()}" for i, paragraph in enumerate(paragraphs)]
        processed_graphs = [{"role": "user", "content": paragraph} for paragraph in paragraphs]
        # print(paragraphs)
        # print(processed_graphs)

        messages = [
            {"role": "system", "content": "You are an expert article-analysis assistant."
                                          # "You WILL respond in JSON format."
                                          "Your job is to analyse paragraphs in the article and look for provocative, emotionally charged, and loaded language"
                                          "You WILL analyse the paragraphs, determine if they are provocative, and if so, output a rating between 1 and 100, 100 being the most provocative."
                                          "you WILL NOT output a summary of the article or the paragraphs."
                                          "Questions you should ask yourself while reading the paragraph:"
                                          "1. What is the literal meaning of the questionable word or phrase?"
                                          "2. What is the emotional or social context of the questionable word or phrase?"
                                          "3. Does that word or phrase have any connotations, that is, associations that are positive or negative?"
                                          "4. What group (sometimes called a “discourse community”) favors one locution over another, and why?"
                                          "5. Is the word or phrase “loaded”?  How far does it steer us from neutral?"
                                          "6. Does the word or phrase help me see, or does it prevent me from seeing? (This is important)"
                                          "You will now be provided with the headline of the article then a paragraph from the article."
                                          "The headline (title of the page) will be provided as \"Headline\": \"EXAMPLE HEADLINE\"."
                                          "The paragraphs will be provided as \"Paragraph (numbered index)\": \"EXAMPLE PARAGRAPH\"."},
            {"role": "user", "content": f"\"Headline\": \"{title}\""}
        ]
        messages.extend(processed_graphs)
        response = await send_chat(messages, "json")
        print(response)
        # TODO: parse `html`, summarise, etc.
        await message.channel.send(f"✅ Article downloaded – {len(processed_html):,} bytes.")
        await send_text_file(message.channel, processed_html)
        # await message.channel.send("Sending thinking portion:")
        # await send_text_file(message.channel, response.message.thinking)
        await message.channel.send("Sending response portion:")
        await send_text_file(message.channel, response.message.content)
    except Exception as exc:
        await message.channel.send("❌ Sorry, an internal error has occurred. Please try again later or contact an administrator.")
        await message.channel.send(f"```\n{exc}\n```")


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
