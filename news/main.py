from __future__ import annotations

import asyncio
import collections
import logging
import os
from pathlib import Path
from typing import Final, Optional, List, NamedTuple
from dataclasses import dataclass
from textwrap import wrap, fill

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
import json

load_dotenv()

DISCORD_TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")

ROLE_NAME = "Newsulizer"

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)

LOGGER = logging.getLogger("main")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s (in %(filename)s:%(lineno)d): %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
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

summary_system_prompt = ("You are a specialized analysis program designed to summarize articles. "
                         "You WILL be given an article and you WILL output a summary of the article in less than 300 words. "
                         "Do NOT include that you are attempting to meet the word count in your response.")

relevance_system_prompt = ("You are a specialized analysis program designed to determine if a paragraph is relevant to the topic of the article. "
                           "You will be given a summary of the article and a paragraph of text. "
                           "You WILL respond with number between 0 and 100 indicating how relevant the paragraph is to the article."
                           "You WILL NOT output anything else besides the number. "
                           "An example response to a given input would be:\n "
                           "-----\n"
                           "Summary:\n "
                           "The president of the United States has been in the White House for 20 years.\n"
                           "-----\n"
                           "Paragraph:\n"
                           "\"The president of the United States has been in the White House for 20 years.\"\n"
                           "-----\n"
                           "Your response to this would then look like:\n"
                           "100")

relevance_system_prompt_2 = "\n".join(["You are a specialized analysis program designed to determine if a paragraph is relevant to the "
                                       "topic of the article based on various snippets and meta-information gathered from the article.",
                                       "You will be given different inputs and prompts by the user where you MUST respond with a "
                                       "YES or NO depending on if that input is relevant to the paragraph."])

@dataclass(frozen=True)
class Response:
    response: ChatResponse

    def content(self):
        return self.response["message"]["content"]

    def tools(self):
        return self.response["message"]["tool_calls"]


class ChatBot:
    def __init__(self, system : str, host : str="192.168.69.3:11434"):
        self.client = AsyncClient(host=host)
        self.messages = []
        self.system = system
        self.model = "llama3.2:3b"
        self.clear()

    async def send_message(self, message : str, **kwargs) -> Response:
        self.messages.append({"role": "user", "content": message})
        response = await self.client.chat(
            model=self.model,
            messages=self.messages,
            stream=False,
            **kwargs)
        self.messages.append({"role": "assistant", "content": response["message"]["content"]})
        return Response(response)

    async def single_chat(self, message : str, **kwargs) -> Response:
        messages = [{"role": "system", "content": self.system}, {"role": "user", "content": message}]
        return Response(await self.client.chat(
            model=self.model,
            messages=messages,
            stream=False,
            **kwargs
        ))

    async def multi_summary(self, message: str, **kwargs) -> list[Response]:
        chunks = wrap(message, width=(4096 - len(self.system) - 64))
        responses = []
        for chunk in chunks:
            responses.append(await self.single_chat(chunk, **kwargs))
        return responses

    async def set_model(self, model : str):
        self.model = model

    def set_system(self, system : str):
        self.system = system
        self.clear()

    def clear(self):
        self.messages = []
        self.messages.append({"role": "system", "content": self.system})

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

async def send_text_file(channel: discord.abc.Messageable, *args: str | tuple[str,str], message: str = "📄 Full article attached:") -> None:
    strings = []
    names = []
    for i, arg in enumerate(args):
        if isinstance(arg, tuple):
            strings.append(arg[1])
            names.append(arg[0])
        else:
            strings.append(arg)
            names.append("Unnamed_file_" + str(i) + ".txt")
    files = [discord.File(io.BytesIO(text.encode("utf-8")), filename=name) for name, text in zip(names, strings)]
    await channel.send(message, files=files)

def tally_responses(array: list[str]):
    yes = 0
    no = 0
    err = 0
    for a in array:
        if a.upper() == "YES":
            yes += 1
        elif a.upper() == "NO":
            no += 1
        else:
            err += 1
    return yes, no, err


async def handle_article_url(message: discord.Message, url: str) -> None:
    LOGGER.info("Received URL from %s: %s", message.author, url)

    try:
        title, processed_html = await article_repository.get_article(url)

        summary_bot = ChatBot(summary_system_prompt)

        summary_parts = await summary_bot.multi_summary(processed_html, options={
            "temperature": 0.5,
            "num_predict": 300,
            "num_ctx": 4096
        })

        summary_bot.set_system("You are a specialized analysis program designed to summarize articles into their key points.\n "
                               "You WILL only output a JSON list of key points, structured as {key_points: [\"keypoint1\", \"keypoint2\",...]}. ")

        try:
            keywords = [item for sublist in (json.loads(sumr.content())["key_points"] for sumr in await summary_bot.multi_summary(processed_html, options={
                "temperature": 0.5,
                "num_ctx": 4096
            })) for item in sublist]
            LOGGER.info(keywords)
        except Exception as exc:
            LOGGER.error("Failed to correctly parse LLM output. It is likely that it has failed.")
            LOGGER.error(exc, exc_info=True)
            keywords = []

        summary_parts_string = [part.content() for part in summary_parts]

        summary = "\n".join(summary_parts_string)

        paragraphs = [para for para in processed_html.split("\n") if len(para.strip()) > 0]

        relevance_bot = ChatBot(relevance_system_prompt)
        relevance_bot2 = ChatBot(relevance_system_prompt_2)

        paragraph_relevance = []
        paragraph_restitutions = []
        paragraph_keypoints = []

        for paragraph in paragraphs:
            response = await relevance_bot.single_chat("".join(["-----\n",
                                               "Summary:\n ",
                                               summary, "-----\n",
                                               "Paragraph:\n ",
                                               paragraph, "-----\n"
                                                                "REMEMBER: You WILL respond with number between 0 and 100 indicating how relevant the paragraph is to the article."]))
            relevance_bot2.clear()
            LOGGER.info(await relevance_bot2.send_message("DO NOT RESPOND TO THIS MESSAGE. The Paragraph you will analyze is as follows:\n\n" + paragraph))
            res = await relevance_bot2.send_message("Is the paragraph relevant to the following summary? Remember, please respond with either YES or NO.\n\n" + summary)
            LOGGER.info(f"Summary Relevancy using chat: {res.content()}")
            restitutions = []
            for keypoint in keywords:
                keypoint_is_rev = await relevance_bot2.send_message(
                    "A key point is an idea that the article is communicating to the reader. Given that, is the paragraph relevant to the following key point. Remember: Please respond with either YES or NO.\n\n" + keypoint)
                LOGGER.info(f"Running for keyword {keypoint} got response {keypoint_is_rev.content()}")
                restitutions.append(keypoint_is_rev.content())
            restitutions.append(res.content())
            yes, no, err = tally_responses(restitutions)
            total = yes + no + err
            paragraph_relevance.append(response.content())
            paragraph_restitutions.append(restitutions)
            paragraph_keypoints.append((yes / total) * 100)

        for i, x in enumerate(paragraph_relevance):
            paragraph_relevance[i] = int(x)

        average_relevance = (sum(int(x) for x in paragraph_relevance) / len(paragraph_relevance) + sum(paragraph_keypoints)) / 2
        median_relevance = sorted(int(ref) for ref in paragraph_relevance)[len(paragraph_relevance) // 2]
        median_relevance2 = sorted(paragraph_keypoints)[len(paragraph_keypoints) // 2]


        relevance_cutoff = min(average_relevance, (median_relevance + median_relevance2) / 2)
        LOGGER.info(f"Relevance cutoff: {relevance_cutoff} From ({average_relevance}, {(median_relevance + median_relevance2) / 2})")

        relevance_content = [fill(para + " (" + str(res) + "%) [" + ",".join(li) + "]" + "(" + str(point) + "%)", 80) for para, res, li, point, in zip(paragraphs, paragraph_relevance, paragraph_restitutions, paragraph_keypoints)]
        relevance_prompt = "\n\n".join(relevance_content)

        # social = await send_chat_with_system("social", processed_html, social_system_prompt, tools)
        # capital = await send_chat_with_system("capital", processed_html, capital_system_prompt, tools)
        # facts = await send_chat_with_system("facts", processed_html, facts_system_prompt, tools)

        # print(social)
        # print(capital)
        # print(facts)

        # social_increment, social_decrement = tally_responses(social['message']["tool_calls"])
        # capital_increment, capital_decrement = tally_responses(capital['message']["tool_calls"])
        # facts_increment, facts_decrement = tally_responses(facts['message']["tool_calls"])

        # TODO: parse `html`, summarise, etc.
        await message.channel.send(f"✅ Article downloaded – {len(processed_html):,} bytes.")
        # time.sleep(0.1)
        # await message.channel.send(f"Social+ {social_increment} | Social- {social_decrement} + Capital+ {capital_increment} | Capital- {capital_decrement} + Facts+ {facts_increment} | Facts- {facts_decrement}")
        time.sleep(0.1)
        # await send_text_file(message.channel, [processed_html, summary, social["message"]["content"], capital["message"]["content"], facts["message"]["content"]], "Files")
        await send_text_file(message.channel, ("Raw Article.txt", processed_html), ("Summary.txt", summary), ("Paragraph Relevance.txt", relevance_prompt), message="Files")
        time.sleep(0.1)
    except Exception as exc:
        await message.channel.send("❌ Sorry, an internal error has occurred. Please try again later or contact an administrator.")
        LOGGER.error(exc, exc_info=True)
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
