r"""Builds the two small files the online demo needs, so the server never needs the 2 GB raw CSV:

    deploy/data/card_memory.json   every card's memory (history + purchases already checked), same format as Redis
    deploy/data/stream.csv.gz      the next purchases to replay through Kafka

Run once on the laptop:  .venv\Scripts\python -m deploy.prepare_data
"""
import json
from pathlib import Path

import pandas as pd

from src.data import load_raw, clean, time_split
from src.streaming.state import empty_card_memory, update_memory, save_bag
from src.streaming.producer import COLUMNS

ALREADY_CHECKED = 211000
REPLAY_COUNT = 50000
OUT = Path(__file__).resolve().parent / "data"


class FileStore:
    """Looks like Redis to save_bag (it has .set), but keeps the text in a dict."""
    def __init__(self):
        self.items = {}

    def set(self, name, value):
        self.items[name] = value


def main():
    new = clean(load_raw("data/raw/card_transaction.v1.csv", start=3_000_000))
    new = new[new["user"] > 252].sort_values("timestamp")
    history, stream = time_split(new, pd.Timestamp("2017-04-25 21:24:36"))

    memory = {}
    for part in (history, stream.iloc[:ALREADY_CHECKED]):
        for _, purchase in part.iterrows():
            key = f'{purchase["user"]}-{purchase["card"]}'
            if key not in memory:
                memory[key] = empty_card_memory()
            update_memory(memory[key], purchase)

    store = FileStore()
    for key, bag in memory.items():
        save_bag(store, key, bag)

    OUT.mkdir(exist_ok=True)
    (OUT / "card_memory.json").write_text(json.dumps(store.items))
    replay = stream.iloc[ALREADY_CHECKED:ALREADY_CHECKED + REPLAY_COUNT][COLUMNS]
    replay.to_csv(OUT / "stream.csv.gz", index=False)
    print(len(memory), "cards,", len(replay), "purchases,", int(replay["is_fraud"].sum()), "frauds")


if __name__ == "__main__":
    main()
