"""Build question -> SQL training pairs for the sales table.
Every SQL query is executed on sales.db, so broken or empty queries are dropped.
Run generate_data.py first."""
import json
import random
import sqlite3

random.seed(7)
TARGET = 3000
con = sqlite3.connect("sales.db")


def fetch(sql):
    return con.execute(sql).fetchall()


CITIES = [r[0] for r in fetch("SELECT DISTINCT customer_city FROM sales")]
CATS = [r[0] for r in fetch("SELECT DISTINCT category FROM sales")]
PAYS = [r[0] for r in fetch("SELECT DISTINCT payment_mode FROM sales")]
PRODUCTS = [r[0] for r in fetch("SELECT DISTINCT product FROM sales")]
YEARS = [2024, 2025]
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

REV = "SUM(total_inr)"
YEAR = "strftime('%Y', order_date)"
YM = "strftime('%Y-%m', order_date)"


def t_total():
    qs = ["What is the total revenue?", "How much did we earn in total?",
          "Total sales amount", "What are our overall sales?", "Show total revenue"]
    return random.choice(qs), f"SELECT {REV} FROM sales;"


def t_rev_by_cat():
    qs = ["Revenue by category", "How much did each category earn?",
          "Show total sales for every category", "Category-wise revenue"]
    return random.choice(qs), f"SELECT category, {REV} AS revenue FROM sales GROUP BY category ORDER BY revenue DESC;"


def t_city_rev():
    c = random.choice(CITIES)
    qs = [f"What is the total revenue from {c}?", f"How much did customers in {c} spend?",
          f"Total sales in {c}", f"Revenue for {c}", f"How much did we earn in {c}?"]
    return random.choice(qs), f"SELECT {REV} FROM sales WHERE customer_city = '{c}';"


def t_top_products():
    n = random.choice([3, 5, 10])
    qs = [f"Top {n} products by revenue", f"Which are the {n} best-selling products by revenue?",
          f"Show the {n} products that earned the most", f"List the {n} highest earning products"]
    return random.choice(qs), f"SELECT product, {REV} AS revenue FROM sales GROUP BY product ORDER BY revenue DESC LIMIT {n};"


def t_orders_by_payment():
    p = random.choice(PAYS)
    qs = [f"How many orders were paid via {p}?", f"Number of {p} orders",
          f"Count orders with payment mode {p}", f"How many {p} orders do we have?"]
    return random.choice(qs), f"SELECT COUNT(*) FROM sales WHERE payment_mode = '{p}';"


def t_avg_order_city():
    qs = ["Average order value by city", "What is the average order amount in each city?",
          "Show average spend per order for every city"]
    return random.choice(qs), "SELECT customer_city, AVG(total_inr) AS avg_order_value FROM sales GROUP BY customer_city ORDER BY avg_order_value DESC;"


def t_monthly_rev():
    y = random.choice(YEARS)
    qs = [f"Monthly revenue in {y}", f"Show month-wise sales for {y}",
          f"How did sales change month by month in {y}?", f"Revenue trend by month for {y}"]
    return random.choice(qs), f"SELECT {YM} AS month, {REV} AS revenue FROM sales WHERE {YEAR} = '{y}' GROUP BY month ORDER BY month;"


def t_top_city():
    qs = ["Which city has the highest revenue?", "Which city earns the most?",
          "Top city by sales", "Where do we make the most money?"]
    return random.choice(qs), f"SELECT customer_city, {REV} AS revenue FROM sales GROUP BY customer_city ORDER BY revenue DESC LIMIT 1;"


def t_cat_year():
    c, y = random.choice(CATS), random.choice(YEARS)
    qs = [f"What was the revenue from {c} in {y}?", f"How much did {c} earn in {y}?",
          f"{c} sales for {y}", f"Total {c} revenue in {y}"]
    return random.choice(qs), f"SELECT {REV} FROM sales WHERE category = '{c}' AND {YEAR} = '{y}';"


def t_avg_discount():
    qs = ["Average discount by category", "What discount do we give on average in each category?",
          "Show the mean discount percentage per category"]
    return random.choice(qs), "SELECT category, AVG(discount_pct) AS avg_discount FROM sales GROUP BY category;"


def t_high_discount():
    d = random.choice([5, 10, 15])
    qs = [f"How many orders had a discount of more than {d}%?", f"Count orders with discount above {d}%",
          f"Number of orders discounted over {d} percent"]
    return random.choice(qs), f"SELECT COUNT(*) FROM sales WHERE discount_pct > {d};"


def t_best_month():
    qs = ["Which month had the highest sales?", "Best month by revenue",
          "In which month did we earn the most?"]
    return random.choice(qs), f"SELECT {YM} AS month, {REV} AS revenue FROM sales GROUP BY month ORDER BY revenue DESC LIMIT 1;"


def t_city_cat():
    c, k = random.choice(CITIES), random.choice(CATS)
    qs = [f"What is the revenue from {k} in {c}?", f"How much {k} did {c} buy in rupees?",
          f"{k} sales in {c}", f"Total {k} revenue for {c}"]
    return random.choice(qs), f"SELECT {REV} FROM sales WHERE customer_city = '{c}' AND category = '{k}';"


def t_units_product():
    p = random.choice(PRODUCTS)
    qs = [f"How many units of {p} were sold?", f"Total quantity sold for {p}",
          f"Number of {p} units sold"]
    return random.choice(qs), f"SELECT SUM(quantity) FROM sales WHERE product = '{p}';"


def t_orders_month():
    y, m = random.choice(YEARS), random.randint(1, 12)
    qs = [f"How many orders were placed in {MONTHS[m - 1]} {y}?", f"Number of orders in {MONTHS[m - 1]} {y}",
          f"Count orders for {MONTHS[m - 1]} {y}"]
    return random.choice(qs), f"SELECT COUNT(*) FROM sales WHERE {YM} = '{y}-{m:02d}';"


TEMPLATES = [t_total, t_rev_by_cat, t_city_rev, t_top_products, t_orders_by_payment,
             t_avg_order_city, t_monthly_rev, t_top_city, t_cat_year, t_avg_discount,
             t_high_discount, t_best_month, t_city_cat, t_units_product, t_orders_month]


def add_noise(question):
    """Mimic how real users type: lowercase, no '?', polite prefixes."""
    if random.random() < 0.3:
        question = question.lower()
    if random.random() < 0.3:
        question = question.rstrip("?")
    if random.random() < 0.2:
        question = random.choice(["please tell me ", "can you show ", "i want to know "]) + question[0].lower() + question[1:]
    return question


pairs, seen = [], set()
for _ in range(50000):
    if len(pairs) >= TARGET:
        break
    question, sql = random.choice(TEMPLATES)()
    question = add_noise(question)
    key = question.strip().lower()
    if key in seen:
        continue
    try:
        rows = fetch(sql)
    except sqlite3.Error:
        continue
    if not rows or rows[0][0] is None:   # drop queries that return nothing
        continue
    seen.add(key)
    pairs.append({"question": question, "sql": sql})

random.shuffle(pairs)
split = int(len(pairs) * 0.9)
for name, part in [("train.jsonl", pairs[:split]), ("val.jsonl", pairs[split:])]:
    with open(name, "w", encoding="utf-8") as f:
        for p in part:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
print(f"{len(pairs)} unique pairs -> train {split}, val {len(pairs) - split}")