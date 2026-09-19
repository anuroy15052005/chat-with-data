from pathlib import Path

FILES = [
    "app.py",
    "llm_client.py",
    "sql_safety.py",
    "data/generate_data.py",
    "data/make_training_data.py",
    "static/index.html",
    "static/style.css",
    "static/script.js",
    "training/finetune.ipynb",
    "hf_space/app.py",
    "hf_space/requirements.txt",
]

EMPTY_NOTEBOOK = '{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}'

for name in FILES:
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        print(f"exists:  {name}")
        continue
    path.write_text(EMPTY_NOTEBOOK if path.suffix == ".ipynb" else "", encoding="utf-8")
    print(f"created: {name}")