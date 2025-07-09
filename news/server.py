import json
import re

from quart import Quart, request, jsonify, abort, send_from_directory
import quart
from pathlib import Path
import logging

# Import the repository class from the existing code base.
# Adjust the relative import path if pool.py lives in a package.
from pool import ArticleRepository

app = Quart(__name__)

article_repository = ArticleRepository()

LOGGER = logging.getLogger("server")

@app.route("/")
async def index():
    return await send_from_directory("static", "index.html")

@app.route("/index.html")
async def index_html():
    return await index()

@app.route("/view.html")
async def view_html():
    return await send_from_directory("static", "view.html")

@app.route("/view")
async def view():
    return await view_html()

@app.route("/browse.html")
async def browse_html():
    return await send_from_directory("static", "browse.html")

@app.route("/browse")
async def browse():
    return await browse_html()

@app.route("/search.html")
async def search_html():
    return await send_from_directory("static", "search.html")

@app.route("/search")
async def search():
    return await search_html()

@app.route("/api/health")
async def health():
    return {"status": "ok"}

@app.route("/api/article/<path:article_url>", methods=["GET"])
async def get_article(article_url: str):
    article = await article_repository.get_article(article_url)
    if article is None:
        abort(404, description="Article not found")
    return jsonify(article)

@app.route("/api/articles", methods=["GET"])
async def get_articles():
    count = min(int(request.args.get("count") or "25"), 125)
    last = int(request.args.get("last") or "-1")
    articles = await article_repository.get_latest_articles(count, last)

    json_obj = []
    for _id, url, title, processed_html in articles:
        json_obj.append({url: {
            "title": title,
            "processed_text": processed_html,
            "id": _id
        }})

    return jsonify(json_obj)

@app.route("/api/search", methods=["GET"])
async def search_articles():
    text = request.args.get("text")
    count = min(int(request.args.get("count") or "25"), 125)
    last = int(request.args.get("last") or "-1")
    if not text:
        abort(400, description="`text` query parameter is required")
    articles = await article_repository.search_articles(text, count, last)

    LOGGER.info(f"Found {len(articles)} articles for search query: {text}")

    json_obj = []
    for _id, url, title, processed_html in articles:
        json_obj.append({url: {
            "title": title,
            "processed_text": processed_html,
            "id": _id
        }})

    return jsonify(json_obj)

@app.route("/api/view_article", methods=["GET"])
async def view_article():
    url = request.args.get("url")
    if not url:
        abort(400, description="`url` query parameter is required")

    article_data = await article_repository.get_paragraphs(url)
    if article_data is None:
        abort(404, description="Article not found")
    article = {
        "title": article_data.title,
        "summary": article_data.summary,
        "topics": article_data.topics,
        "topics_map": article_data.topics_map,
        "paragraphs": {}
    }
    for paragraph_id, paragraph_text in article_data.paragraphs:
        article["paragraphs"][paragraph_id] = {
            "text": paragraph_text,
            "topic_ratings": [],
            "summary_rating": article_data.summary_rating.get(paragraph_id)
        }

        for topic_id, topic, rating in article_data.paragraph_ratings[paragraph_id]:
            article["paragraphs"][paragraph_id]["topic_ratings"].append({
                "id": topic_id,
                "topic": topic,
                "rating": (True if (re.search("YES", rating)) else False)
            })
    return jsonify(article)


@app.route("/article-by-url", methods=["GET"])
async def get_article_by_url():
    url = request.args.get("url")
    if not url:
        abort(400, description="`url` query parameter is required")

    LOGGER.info(f"Fetching article by URL: {url}")
    article = await article_repository.get_article(url)
    if article is None:
        abort(404, description="Article not found")
    return jsonify(article)
