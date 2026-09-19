"""Generate a synthetic Indian sales dataset -> sales.csv + sales.db (SQLite)."""
import csv
import random
import sqlite3
from datetime import date, timedelta

random.seed(42)
N_ROWS = 20000

CITIES = ["Delhi", "Mumbai", "Bengaluru", "Kolkata", "Chennai", "Hyderabad",
          "Pune", "Lucknow", "Jaipur", "Kanpur", "Ahmedabad", "Chandigarh"]

# category -> {product: (min_price_inr, max_price_inr)}
CATALOG = {
    "Electronics": {"Smartphone": (8000, 60000), "Headphones": (500, 8000),
                    "Smartwatch": (1500, 25000), "Power Bank": (600, 3000)},
    "Clothing": {"T-Shirt": (300, 1500), "Jeans": (800, 3500),
                 "Kurta": (500, 3000), "Saree": (900, 8000)},
    "Home & Kitchen": {"Mixer Grinder": (2000, 6000), "Pressure Cooker": (900, 3500),
                       "Bedsheet Set": (600, 3000), "Water Bottle": (200, 1200)},
    "Groceries": {"Basmati Rice 5kg": (450, 900), "Cooking Oil 5L": (700, 1100),
                  "Tea Pack": (150, 600), "Dry Fruits Box": (400, 2000)},
    "Books": {"Novel": (150, 600), "Exam Guide": (300, 1200), "Notebook Pack": (100, 400)},
}
PAYMENT_MODES = ["UPI", "Credit Card", "Debit Card", "Cash on Delivery", "Net Banking"]
PAYMENT_WEIGHTS = [45, 15, 15, 20, 5]

# Every day in 2024-2025; festive season (20 Oct - 10 Nov) gets 3x weight
days = [date(2024, 1, 1) + timedelta(days=i) for i in range(731)]
weights = [3 if (10, 20) <= (d.month, d.day) <= (11, 10) else 1 for d in days]
order_dates = sorted(random.choices(days, weights=weights, k=N_ROWS))

rows = []
for i, d in enumerate(order_dates, start=1):
    category = random.choice(list(CATALOG))
    product = random.choice(list(CATALOG[category]))
    lo, hi = CATALOG[category][product]
    unit_price = round(random.randint(lo, hi) / 10) * 10
    qty = random.choices([1, 2, 3, 4, 5], [50, 25, 12, 8, 5])[0]
    discount = random.choice([0, 0, 0, 5, 10, 15, 20])
    total = round(qty * unit_price * (1 - discount / 100), 2)
    rows.append((i, d.isoformat(), random.choice(CITIES), category, product, qty,
                 unit_price, discount,
                 random.choices(PAYMENT_MODES, PAYMENT_WEIGHTS)[0], total))

COLUMNS = ["order_id", "order_date", "customer_city", "category", "product",
           "quantity", "unit_price_inr", "discount_pct", "payment_mode", "total_inr"]

with open("sales.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(COLUMNS)
    writer.writerows(rows)

con = sqlite3.connect("sales.db")
con.execute("DROP TABLE IF EXISTS sales")
con.execute("""CREATE TABLE sales (
    order_id INTEGER PRIMARY KEY, order_date TEXT, customer_city TEXT,
    category TEXT, product TEXT, quantity INTEGER, unit_price_inr INTEGER,
    discount_pct INTEGER, payment_mode TEXT, total_inr REAL)""")
con.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
con.commit()
con.close()
print(f"Created sales.csv and sales.db with {len(rows)} rows")