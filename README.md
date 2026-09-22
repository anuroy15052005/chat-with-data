# Chat with Data

A small Flask application that lets you ask natural-language questions about a local sales dataset. Groq generates a read-only SQLite query, the application validates it, and the result is shown in a lightweight web interface.

## Features

- Ask questions about revenue, orders, units, cities, categories, products, and payment modes.
- Generate SQL with the Groq Chat Completions API.
- Allow only `SELECT` and `WITH` queries through a read-only SQLite connection.
- Display the answer, result table, and generated SQL.
- Apply per-minute and per-day request limits.

## Requirements

- Python 3.10 or newer
- A Groq API key
- Windows PowerShell, macOS/Linux shell, or an equivalent terminal

## Setup

Open a terminal in the project directory and create or activate a virtual environment:

```powershell
conda activate chatD
```

Or with Python's built-in environment support:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
LLM_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b
MAX_QUESTIONS_PER_MIN=10
EXPLAIN_WITH_LLM=false
```

Keep `.env` private. Never commit an API key to source control.

## Run

The repository includes `sales.db`. If it is missing or you want to recreate the deterministic sample data, run:

```powershell
python data\generate_data.py
```

Start the development server:

```powershell
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in a browser. The health endpoint is available at [http://127.0.0.1:5000/health](http://127.0.0.1:5000/health).

## Project layout

```text
app.py                 Flask routes and request handling
llm_client.py          Groq API integration
sql_safety.py          SQL validation and read-only execution
sales.db               SQLite sales database
data/generate_data.py  Rebuild sales.csv and sales.db
static/                Browser interface
schema.txt             Database schema supplied to the model
requirements.txt       Python dependencies
```

## Example questions

- Which city had the highest revenue in 2024?
- What is the total revenue by category?
- Which product sold the most units?
- What is the average order value by payment mode?

## Troubleshooting

**The homepage is blank**

Confirm that `static/index.html`, `static/style.css`, and `static/script.js` exist, then restart Flask and refresh the browser.

**The model service returns 404**

The configured model may no longer be available. Check the current Groq model list and update `GROQ_MODEL` in `.env`.

**The model service returns 429**

The Groq free-tier rate limit has been reached. Wait and try again, or review the limits for your API key.

**The database is missing**

Run `python data\generate_data.py` from the project root.