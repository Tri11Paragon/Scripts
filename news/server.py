from flask import Flask, request, jsonify, abort
from pathlib import Path
import logging

# Import the repository class from the existing code base.
# Adjust the relative import path if pool.py lives in a package.
from pool import ArticleRepository

app = Flask(__name__)

article_repository = ArticleRepository()

LOGGER = logging.getLogger("server")

@app.route("/articles/<article_url>", methods=["GET"])
def get_article(article_url: str):
    article = article_repository.get_article(article_url)
    if article is None:
        abort(404, description="Article not found")
    return jsonify(article)

@app.route("/article-by-url", methods=["GET"])
def get_article_by_url():
    url = request.args.get("url")
    if not url:
        abort(400, description="`url` query parameter is required")

    LOGGER.info(f"Fetching article by URL: {url}")
    article = article_repository.get_article(url)
    if article is None:
        abort(404, description="Article not found")
    return jsonify(article)
