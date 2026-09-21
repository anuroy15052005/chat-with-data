"""Build question -> SQL training pairs for the sales table.

Questions are assembled from parts (metric + filters + grouping), so the model
sees many combinations instead of a few fixed sentences. Every SQL query is
executed on sales.db and dropped if it fails or returns nothing.

Run generate_data.py first. Writes train.jsonl, val.jsonl and schema.txt."""
import json
import random
import re
import sqlite3
from collections import Counter

random.seed(7)
TARGET = 6000
con = sqlite3.connect("sales.db")


def fetch(sql):
    return con.execute(sql).fetchall()


CITIES = sorted(r[0] for r in fetch("SELECT DISTINCT customer_city FROM sales"))
PAYS = sorted(r[0] for r in fetch("SELECT DISTINCT payment_mode FROM sales"))
CATEGORY_PRODUCTS = {}
for cat, prod in fetch("SELECT DISTINCT category, product FROM sales ORDER BY category, product"):
    CATEGORY_PRODUCTS.setdefault(cat, []).append(prod)
CATS = list(CATEGORY_PRODUCTS)
PRODUCTS = [p for ps in CATEGORY_PRODUCTS.values() for p in ps]
YEARS = [2024, 2025]
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# metric -> (sql aggregate, alias, nouns, single-value question stems)
METRICS = {
    "revenue": ("SUM(total_inr)", "revenue", ["revenue", "sales", "total revenue", "total sales"],
                ["What is the total revenue {f}?", "Total sales {f}", "How much did we earn {f}?",
                 "Show me the revenue {f}"]),
    "orders": ("COUNT(*)", "orders", ["number of orders", "order count"],
               ["How many orders {f}?", "Number of orders {f}", "Count the orders {f}"]),
    "units": ("SUM(quantity)", "units", ["units sold", "quantity sold"],
              ["How many units were sold {f}?", "Total units sold {f}", "Total quantity sold {f}"]),
    "aov": ("AVG(total_inr)", "avg_order_value", ["average order value", "average order amount"],
            ["What is the average order value {f}?", "Average order value {f}", "Average order amount {f}"]),
    "discount": ("AVG(discount_pct)", "avg_discount", ["average discount", "mean discount percentage"],
                 ["What is the average discount {f}?", "Average discount {f}", "Mean discount percentage {f}"]),
}

# dimension -> (sql expression, alias, singular words, plural words)
DIMS = {
    "city": ("customer_city", "customer_city", ["city"], ["cities"]),
    "category": ("category", "category", ["category"], ["categories"]),
    "product": ("product", "product", ["product"], ["products"]),
    "payment": ("payment_mode", "payment_mode", ["payment mode", "payment method"],
                ["payment modes", "payment methods"]),
    "month": ("strftime('%Y-%m', order_date)", "month", ["month"], ["months"]),
    "year": ("strftime('%Y', order_date)", "year", ["year"], ["years"]),
}
# filters that make no sense when grouping by a given dimension
AVOID = {"city": {"city"}, "category": {"category", "product"}, "product": {"product"},
         "payment": {"payment"}, "month": {"month"}, "year": {"year", "month"}}

FILTER_ORDER = ["city", "category", "product", "payment", "year", "month", "discount"]


def make_filter(kind):
    """Return (sql condition, phrase) for one filter."""
    if kind == "city":
        v = random.choice(CITIES)
        return f"customer_city = '{v}'", random.choice([f"in {v}", f"from {v}", f"for customers in {v}"])
    if kind == "category":
        v = random.choice(CATS)
        return f"category = '{v}'", random.choice([f"for {v}", f"in the {v} category", f"of {v}"])
    if kind == "product":
        v = random.choice(PRODUCTS)
        return f"product = '{v}'", random.choice([f"for {v}", f"of {v}"])
    if kind == "payment":
        v = random.choice(PAYS)
        return f"payment_mode = '{v}'", random.choice([f"paid via {v}", f"using {v}", f"paid with {v}"])
    if kind == "year":
        y = random.choice(YEARS)
        return f"strftime('%Y', order_date) = '{y}'", f"in {y}"
    if kind == "month":
        y, m = random.choice(YEARS), random.randint(1, 12)
        return f"strftime('%Y-%m', order_date) = '{y}-{m:02d}'", f"in {MONTHS[m - 1]} {y}"
    n = random.choice([5, 10, 15])
    return f"discount_pct > {n}", random.choice([f"with discount above {n}%", f"with more than {n}% discount"])


def pick_filters(avoid):
    """Choose 0-3 compatible filters. Returns (' WHERE ...' or '', phrase)."""
    kinds = [k for k in FILTER_ORDER if k not in avoid]
    chosen = []
    for k in random.sample(kinds, min(random.choice([0, 1, 1, 2, 2, 3]), len(kinds))):
        if k in ("category", "product") and {"category", "product"} & set(chosen):
            continue
        if k in ("year", "month") and {"year", "month"} & set(chosen):
            continue
        chosen.append(k)
    chosen.sort(key=FILTER_ORDER.index)          # fixed SQL order, so the model sees one style
    parts = [make_filter(k) for k in chosen]
    phrases = [p for _, p in parts]
    random.shuffle(phrases)                      # but the wording order varies
    where = " WHERE " + " AND ".join(c for c, _ in parts) if parts else ""
    return where, " ".join(phrases)


def select_clause(dim):
    expr, alias, _, _ = DIMS[dim]
    return expr if expr == alias else f"{expr} AS {alias}"


def shape_value():
    agg, _, _, stems = METRICS[random.choice(list(METRICS))]
    where, f = pick_filters(set())
    return random.choice(stems).format(f=f), f"SELECT {agg} FROM sales{where};"


def shape_group():
    agg, alias, nouns, _ = METRICS[random.choice(list(METRICS))]
    dim = random.choice(list(DIMS))
    _, dalias, singles, _ = DIMS[dim]
    where, f = pick_filters(AVOID[dim])
    noun, word = random.choice(nouns), random.choice(singles)
    q = random.choice([f"{noun.capitalize()} by {word} {f}", f"Show {noun} for each {word} {f}",
                       f"{noun.capitalize()} per {word} {f}"])
    order = dalias if dim in ("month", "year") else f"{alias} DESC"
    return q, (f"SELECT {select_clause(dim)}, {agg} AS {alias} FROM sales{where} "
               f"GROUP BY {dalias} ORDER BY {order};")


def shape_top():
    agg, alias, nouns, _ = METRICS[random.choice(list(METRICS))]
    dim = random.choice([d for d in DIMS if d != "year"])
    _, dalias, singles, plurals = DIMS[dim]
    where, f = pick_filters(AVOID[dim])
    noun = random.choice(nouns)
    if random.random() < 0.35:
        n = random.choice([3, 5])
        q, order, limit = f"Top {n} {random.choice(plurals)} by {noun} {f}", "DESC", n
    else:
        way = random.choice(["highest", "highest", "lowest"])
        q = f"Which {random.choice(singles)} has the {way} {noun} {f}?"
        order, limit = ("DESC" if way == "highest" else "ASC"), 1
    return q, (f"SELECT {select_clause(dim)}, {agg} AS {alias} FROM sales{where} "
               f"GROUP BY {dalias} ORDER BY {alias} {order} LIMIT {limit};")


SHAPES = [(shape_value, 0.40), (shape_group, 0.25), (shape_top, 0.35)]


def tidy(q):
    q = re.sub(r"\s+", " ", q).strip()
    return re.sub(r"\s+\?", "?", q)


def add_noise(q):
    """Mimic how people type: lowercase, no '?', polite prefixes."""
    if random.random() < 0.3:
        q = q.lower()
    if random.random() < 0.3:
        q = q.rstrip("?")
    if random.random() < 0.2:
        q = random.choice(["please tell me ", "can you show ", "i want to know "]) + q[0].lower() + q[1:]
    return q


pairs, seen, shape_counts = [], set(), Counter()
for _ in range(200000):
    if len(pairs) >= TARGET:
        break
    shape = random.choices([s for s, _ in SHAPES], [w for _, w in SHAPES])[0]
    question, sql = shape()
    question = add_noise(tidy(question))
    key = question.lower()
    if key in seen:
        continue
    try:
        rows = fetch(sql)
    except sqlite3.Error:
        continue
    if not rows or rows[0][-1] is None or rows[0][-1] == 0:   # nothing useful returned
        continue
    seen.add(key)
    shape_counts[shape.__name__] += 1
    pairs.append({"question": question, "sql": sql})

random.shuffle(pairs)
split = int(len(pairs) * 0.9)
for name, part in [("train.jsonl", pairs[:split]), ("val.jsonl", pairs[split:])]:
    with open(name, "w", encoding="utf-8") as f:
        for p in part:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

# The model must see which values belong to which column, in training and at answer time
schema = (
    "sales(order_id INTEGER, order_date TEXT 'YYYY-MM-DD', customer_city TEXT, category TEXT, "
    "product TEXT, quantity INTEGER, unit_price_inr INTEGER, discount_pct INTEGER, "
    "payment_mode TEXT, total_inr REAL)\n"
    f"customer_city: {', '.join(CITIES)}\n"
    "category -> products: " + "; ".join(f"{c}: {', '.join(ps)}" for c, ps in CATEGORY_PRODUCTS.items()) + "\n"
    f"payment_mode: {', '.join(PAYS)}\n"
    "order_date: 2024-01-01 to 2025-12-31. total_inr is revenue in INR."
)
with open("schema.txt", "w", encoding="utf-8") as f:
    f.write(schema)

print(f"{len(pairs)} unique pairs -> train {split}, val {len(pairs) - split}")
print(dict(shape_counts))
