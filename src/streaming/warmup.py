"""One-time warm-up: build every card's memory from past purchases and save it to Redis.

Run once (from the project folder) before starting the consumer:
    .venv\\Scripts\\python -m src.streaming.warmup
"""
import pandas as pd
import redis

from src.data import load_raw, clean, time_split
from src.streaming.state import empty_card_memory, update_memory, save_bag

ALREADY_CHECKED = 211000   # stream purchases before this were already scored, so they count as history


def main():
    new = clean(load_raw("data/raw/card_transaction.v1.csv", start=3_000_000))
    new = new[new["user"] > 252].sort_values("timestamp")
    cutoff = pd.Timestamp("2017-04-25 21:24:36")
    history, stream = time_split(new, cutoff)

    memory = {}
    for part in (history, stream.iloc[:ALREADY_CHECKED]):
        for _, purchase in part.iterrows():
            key = f'{purchase["user"]}-{purchase["card"]}'
            if key not in memory:
                memory[key] = empty_card_memory()
            update_memory(memory[key], purchase)

    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    for key, bag in memory.items():
        save_bag(r, key, bag)
    print(len(memory), "card memories saved to Redis")


if __name__ == "__main__":
    main()
