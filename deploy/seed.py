"""Fills Redis with every card's memory from card_memory.json and empties the prediction log.

Called at start-up and again before each replay starts over, so memory never gets duplicate purchases.
"""
import json
import sqlite3
from pathlib import Path

from src.connections import redis_client
from src.monitoring.prediction_log import init_db

DATA = Path(__file__).resolve().parent / "data"


def seed():
    r = redis_client()
    items = json.loads((DATA / "card_memory.json").read_text())
    r.flushdb()
    r.mset(items)
    conn = init_db()
    conn.execute("DELETE FROM predictions")
    conn.commit()
    conn.close()
    print(len(items), "card memories loaded, prediction log emptied")


if __name__ == "__main__":
    seed()
