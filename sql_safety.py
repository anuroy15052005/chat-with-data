import re
import sqlite3
import time
from pathlib import Path

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|reindex|truncate)\b",
    re.IGNORECASE,
)


class UnsafeSQL(ValueError):
    pass


def clean_sql(text):
    """Remove markdown code fences and a trailing semicolon from model output."""
    text = re.sub(r"^```(?:sql)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    return text.strip().rstrip(";").strip()


def validate_sql(text):
    sql = clean_sql(text)
    if not re.match(r"(?is)^(select|with)\b", sql):
        raise UnsafeSQL("Only SELECT queries are allowed.")
    if ";" in sql or "--" in sql or "/*" in sql:
        raise UnsafeSQL("Only one plain statement is allowed.")
    if FORBIDDEN.search(sql):
        raise UnsafeSQL("The query contains a blocked keyword.")
    return sql


def run_query(text, db_path, max_rows=100, timeout_s=3):
    """Validate, then run on a read-only connection. Returns (sql, columns, rows)."""
    sql = validate_sql(text)
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    deadline = time.monotonic() + timeout_s
    con.set_progress_handler(lambda: time.monotonic() > deadline, 10000)
    try:
        cur = con.execute(sql)
        columns = [c[0] for c in cur.description]
        return sql, columns, cur.fetchmany(max_rows)
    finally:
        con.close()