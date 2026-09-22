import os
import sqlite3

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

import llm_client
from sql_safety import UnsafeSQL, run_query

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sales.db")
PER_MIN = int(os.getenv("MAX_QUESTIONS_PER_MIN", "10"))
# Off by default: each explanation is one more call against the free quota.
EXPLAIN_WITH_LLM = os.getenv("EXPLAIN_WITH_LLM", "false").lower() == "true"

app = Flask(__name__, static_folder="static", static_url_path="")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)  # real client IP behind Render's proxy
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

if not os.path.exists(DB_PATH):
    print("WARNING: sales.db not found. Run: python data/generate_data.py")


class CannotAnswer(Exception):
    pass


def get_result(question):
    """Ask the model for SQL, run it, and retry once with the error if it fails."""
    sql, error = None, None
    for _ in range(2):
        raw = llm_client.generate_sql(question, sql, error)
        if raw.upper().startswith("CANNOT_ANSWER"):
            raise CannotAnswer()
        try:
            return run_query(raw, DB_PATH)
        except (UnsafeSQL, sqlite3.Error) as e:
            sql, error, last = raw, str(e), e
    raise last


def simple_answer(columns, rows):
    if not rows:
        return "No matching data found."
    if len(rows) == 1 and len(columns) == 1:
        value = rows[0][0]
        money = "revenue" in columns[0].lower() or "total" in columns[0].lower() or "sum" in columns[0].lower()
        if isinstance(value, float):
            value = f"{value:,.2f}"
        return f"{'₹' if money else ''}{value}"
    return ""


@app.get("/")
def home():
    return app.send_static_file("index.html")


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/ask")
@limiter.limit(f"{PER_MIN} per minute")
@limiter.limit("100 per day")
def ask():
    question = ((request.get_json(silent=True) or {}).get("question") or "").strip()
    if not question:
        return jsonify(error="Please type a question."), 400
    if len(question) > 300:
        return jsonify(error="Please keep the question under 300 characters."), 400

    try:
        sql, columns, rows = get_result(question)
    except llm_client.LLMError as e:
        return jsonify(error=str(e)), (503 if e.busy else 502)
    except CannotAnswer:
        return jsonify(error="I can't answer that from the sales data. Try asking about "
                             "revenue, orders, cities, categories or products."), 422
    except (UnsafeSQL, sqlite3.Error):
        return jsonify(error="I couldn't turn that into a valid query. Try rephrasing."), 422

    answer = simple_answer(columns, rows)
    if EXPLAIN_WITH_LLM and rows:
        try:
            answer = llm_client.explain(question, columns, rows)
        except llm_client.LLMError:
            pass  # keep the simple answer

    return jsonify(sql=sql, columns=columns, rows=rows, answer=answer)


@app.errorhandler(429)
def too_many(_):
    return jsonify(error="Too many questions. Please wait a minute and try again."), 429


if __name__ == "__main__":
    app.run(debug=True)