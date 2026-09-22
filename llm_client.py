import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Change GROQ_MODEL in .env if Groq changes the available model list.
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA = open(os.path.join(BASE_DIR, "schema.txt"), encoding="utf-8").read().strip()

SQL_SYSTEM = f"""You write one SQLite query that answers the user's question about this table.

{SCHEMA}

Rules:
- Return ONLY the SQL. No explanation, no markdown.
- category and product are different columns. A category contains several products (see the list above).
- Revenue or sales means SUM(total_inr). Orders means COUNT(*). Units means SUM(quantity). All money is in Indian rupees.
- Use strftime for dates, for example strftime('%Y-%m', order_date).
- Use the exact spelling of city, category, product and payment values from the list above.
- Add LIMIT 50 unless the question asks for a specific number of rows.
- If the question cannot be answered from this table, return exactly: CANNOT_ANSWER

Examples:
Q: units of Headphones sold in Pune in 2024
SQL: SELECT SUM(quantity) FROM sales WHERE product = 'Headphones' AND customer_city = 'Pune' AND strftime('%Y', order_date) = '2024';
Q: which city has the highest revenue from Groceries?
SQL: SELECT customer_city, SUM(total_inr) AS revenue FROM sales WHERE category = 'Groceries' GROUP BY customer_city ORDER BY revenue DESC LIMIT 1;
Q: average order value by payment mode
SQL: SELECT payment_mode, AVG(total_inr) AS avg_order_value FROM sales GROUP BY payment_mode ORDER BY avg_order_value DESC;
"""

EXPLAIN_SYSTEM = (
    "You explain query results to a business user in 1 to 3 plain sentences. "
    "Use only the numbers given. Show money with the rupee sign."
)


class LLMError(Exception):
    def __init__(self, message, busy=False):
        super().__init__(message)
        self.busy = busy


def _generate(prompt, system):
    key = os.getenv("LLM_API_KEY")
    if not key:
        raise LLMError("LLM_API_KEY is missing. Add your Groq key to the .env file.")
    try:
        r = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": MODEL, "temperature": 0, "max_tokens": 400,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": prompt}]},
            timeout=30,
        )
    except requests.RequestException:
        raise LLMError("Could not reach the model service. Please try again.")

    if r.status_code == 429:
        raise LLMError("The free Groq limit is reached for now. Try again in a minute.", busy=True)
    if r.status_code == 404:
        raise LLMError(f"The Groq model '{MODEL}' was not found. Update GROQ_MODEL in .env.")
    if r.status_code in (401, 403):
        raise LLMError("The Groq API key was rejected. Check LLM_API_KEY.")
    if not r.ok:
        raise LLMError(f"The model service returned an error ({r.status_code}).")
    try:
        return (r.json()["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, ValueError):
        raise LLMError("The model service sent an unexpected reply.")


def generate_sql(question, previous_sql=None, error=None):
    prompt = f"Q: {question}"
    if error:
        prompt += (f"\n\nYour previous query failed.\nQuery: {previous_sql}\n"
                   f"Error: {error}\nWrite a corrected query.")
    return _generate(prompt, SQL_SYSTEM)


def explain(question, columns, rows):
    table = "\n".join(str(dict(zip(columns, r))) for r in rows[:20])
    return _generate(f"Question: {question}\nResult rows:\n{table}", EXPLAIN_SYSTEM)