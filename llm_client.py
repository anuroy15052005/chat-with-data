import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

# Check which models show a free tier in Google AI Studio; change it in .env if needed.
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

SQL_SYSTEM = """You write SQLite queries for one table.

Table sales(order_id INTEGER, order_date TEXT 'YYYY-MM-DD', customer_city TEXT,
category TEXT, product TEXT, quantity INTEGER, unit_price_inr INTEGER,
discount_pct INTEGER, payment_mode TEXT, total_inr REAL)

customer_city is one of: Delhi, Mumbai, Bengaluru, Kolkata, Chennai, Hyderabad, Pune,
Lucknow, Jaipur, Kanpur, Ahmedabad, Chandigarh.
category is one of: Electronics, Clothing, Home & Kitchen, Groceries, Books.
payment_mode is one of: UPI, Credit Card, Debit Card, Cash on Delivery, Net Banking.
Dates run from 2024-01-01 to 2025-12-31.

Rules:
- Return ONLY one SELECT statement. No explanation, no markdown.
- Revenue or sales means SUM(total_inr). All money is in Indian rupees.
- Use strftime for dates, for example strftime('%Y-%m', order_date).
- Add LIMIT 50 unless the question asks for a specific number of rows.
- If the question cannot be answered from this table, return exactly: CANNOT_ANSWER
"""

EXPLAIN_SYSTEM = (
    "You explain query results to a business user in 1 to 3 plain sentences. "
    "Use only the numbers given. Show money with the rupee sign."
)

_client = None


class LLMError(Exception):
    def __init__(self, message, busy=False):
        super().__init__(message)
        self.busy = busy


def _generate(prompt, system):
    global _client
    try:
        if _client is None:
            _client = genai.Client(api_key=os.getenv("LLM_API_KEY"))
        response = _client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system, temperature=0),
        )
    except errors.APIError as e:
        if e.code == 429:
            raise LLMError("The free Gemini quota is used up for now. Try again in a minute.", busy=True)
        raise LLMError(f"The model service returned an error ({e.code}).")
    except ValueError:
        raise LLMError("LLM_API_KEY is missing. Add it to your .env file.")
    return (response.text or "").strip()


def generate_sql(question, previous_sql=None, error=None):
    prompt = f"Question: {question}"
    if error:
        prompt += (f"\n\nYour previous query failed.\nQuery: {previous_sql}\n"
                   f"Error: {error}\nWrite a corrected query.")
    return _generate(prompt, SQL_SYSTEM)


def explain(question, columns, rows):
    table = "\n".join(str(dict(zip(columns, r))) for r in rows[:20])
    return _generate(f"Question: {question}\nResult rows:\n{table}", EXPLAIN_SYSTEM)