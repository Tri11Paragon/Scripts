from flask import Flask, request, jsonify, abort
from pathlib import Path

# Import the repository class from the existing code base.
# Adjust the relative import path if pool.py lives in a package.
from pool import ArticleRepository

app = Flask(__name__)

article_repository = ArticleRepository()

@app.route("/articles/<article_url>", methods=["GET"])
def get_article(article_url: str):
    """
    Fetch one article by its numeric primary key.
    Responds with the whole row in JSON or 404 if not present.
    """
    article = article_repository.get_article(article_url)
    if article is None:
        abort(404, description="Article not found")
    return jsonify(article)

@app.route("/article-by-url", methods=["GET"])
def get_article_by_url():
    """
    Same as above but lets a client specify the canonical URL instead of the ID:

    GET /article-by-url?url=https://example.com/foo
    """
    url = request.args.get("url")
    if not url:
        abort(400, description="`url` query parameter is required")

    article = await article_repository.get_article(url)
    if article is None:
        abort(404, description="Article not found")
    return jsonify(article)
