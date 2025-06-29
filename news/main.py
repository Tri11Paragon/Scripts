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
import time

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

social_system_prompt = ("You are a specialized analysis program designed to determine if articles are pro-social. "
                        "Pro-social text contains topics such as raising concerns about the negative effects on workers, the environment, "
                        "or on society as a whole (as in the concerns of the 99%, or the proletariat). "
                        "You WILL give rating of this article by calling the increment tool if you read a paragraph (seperated by newlines) which is pro-society, and decrement if it is anti-society. "
                        "You WILL respond explaining why you have called the tools you did. "
                        "You ARE allowed to answer with \"this article doesn't require social analysis\" if the topic is not relevant to social interests. "
                        "You ARE allowed to not make calls to your tools if the topic is not relevant to social interests. ")

capital_system_prompt = ("You are a specialized analysis program designed to determine if articles are pro-capital. "
                         "Pro-capital text is concerned but not limited to the interests of business, or of the rich and elite. "
                         "You WILL give rating of this article by calling the increment tool if you read a paragraph (seperated by newlines) which is pro-capital, and decrement if it is anti-capital. "
                         "you ARE allowed to call the tools multiple times. "
                         "You WILL respond explaining why you have called the tools you did. "
                         "You ARE allowed to answer with \"this article doesn't require capital analysis\" if the topic is not relevant to capital interests. "
                         "You ARE allowed to not make calls to your tools if the topic is not relevant to capital interests. ")

facts_system_prompt = ("You are a specialized analysis program designed to determine if articles are attempting to accurately represent facts. "
                       "You are not checking if the facts presented in the article are correct, "
                       "rather you are to determine if an attempt was made to represent multiple sides of the issue. "
                       "This can range from only presenting the news in the form of events that happened or expert comments "
                       "(therefore not introducing the writer's opinion into the article), to not using too much emotional language "
                       "(emotional language can be fine, if for example the article is trying to communicate that one side has commited genocide, "
                       "it is okay to be emotional over that topic and should probably be encouraged. "
                       "If the article only presents opinions about genocide, then it is not accurately representing what happened). "
                       "You WILL give rating of this article by calling the increment tool if you read a paragraph (seperated by newlines) which is accurately representing facts, and decrement if it is not.")

async def send_chat(model, messages, tools = None):
    return await AsyncClient(host="192.168.69.3:11434").chat(
        model=model,
        messages=messages,
        stream=False,
        tools=tools,
        options={
            'temperature': 0.5,
            # "num_ctx": 128000
        })
    # return await AsyncClient(host="192.168.69.3:11434").generate(model=model, prompt=messages, stream=False)

async def send_chat_with_system(model, message, system, tools = None):
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': message}]
    return await send_chat(model, messages, tools)

async def send_text_file(channel: discord.abc.Messageable, content: str, message: str = "📄 Full article attached:", filename: str = "article.md") -> None:
    fp = io.BytesIO(content.encode("utf-8"))
    file = discord.File(fp, filename=filename)
    await channel.send(message, file=file)

def tally_responses(tools):
    increment = 0
    decrement = 0
    if tools:
        for tool in tools:
            if tool['function']['name'] == "increment":
                increment += 1
            elif tool['function']['name'] == "decrement":
                decrement += 1
            else:
                LOGGER.warning(f"Unknown tool: {tool}")
    return increment, decrement


async def handle_article_url(message: discord.Message, url: str) -> None:
    LOGGER.info("Received URL from %s: %s", message.author, url)

    try:
        title, processed_html = await article_repository.get_article(url)

        tools = [
            {
                'type': 'function',
                'function': {
                    'name': 'increment',
                    'description': 'increment internal counter by 1',
                    'parameters': {
                        'type': 'object',
                        'properties': {},
                        'required': []
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'decrement',
                    'description': 'decrement internal counter by 1',
                    'parameters': {
                        'type': 'object',
                        'properties': {},
                        'required': []
                    }
                }
            }
        ]

        social = await send_chat_with_system("social", processed_html, social_system_prompt, tools)
        capital = await send_chat_with_system("capital", processed_html, capital_system_prompt, tools)
        facts = await send_chat_with_system("facts", processed_html, facts_system_prompt, tools)

        print(social)
        print(capital)
        print(facts)

        social_increment, social_decrement = tally_responses(social['message']["tool_calls"])
        capital_increment, capital_decrement = tally_responses(capital['message']["tool_calls"])
        facts_increment, facts_decrement = tally_responses(facts['message']["tool_calls"])

        # TODO: parse `html`, summarise, etc.
        await message.channel.send(f"✅ Article downloaded – {len(processed_html):,} bytes.")
        time.sleep(0.1)
        await send_text_file(message.channel, processed_html)
        time.sleep(0.1)
        await send_text_file(message.channel, social["message"]["content"], "Social calculations:")
        time.sleep(0.1)
        await message.channel.send(f"Social+ {social_increment} | Social- {social_decrement}")
        time.sleep(0.1)
        await send_text_file(message.channel, capital["message"]["content"], "capital calculations:")
        time.sleep(0.1)
        await message.channel.send(f"Capital+ {capital_increment} | Capital- {capital_decrement}")
        time.sleep(0.1)
        await send_text_file(message.channel, facts["message"]["content"], "facts calculations:")
        time.sleep(0.1)
        await message.channel.send(f"Facts+ {facts_increment} | Facts- {facts_decrement}")
        time.sleep(0.1)
    except Exception as exc:
        await message.channel.send("❌ Sorry, an internal error has occurred. Please try again later or contact an administrator.")
        await message.channel.send(f"```\n{exc}\n```")
        LOGGER.error(exc, exc_info=True)


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
