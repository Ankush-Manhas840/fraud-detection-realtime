"""Writes every prediction to SQLite (one file, predictions.db) so the system can be monitored with SQL."""
import sqlite3

from src.config import ROOT, load_config

DB_PATH = ROOT / load_config()["monitoring"]["prediction_db"]


def init_db():
    """Open the database, creating the predictions table if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            ts TEXT,
            card TEXT,
            amount REAL,
            score REAL,
            flagged INTEGER,
            is_fraud INTEGER,
            new_shop INTEGER,
            outside_us INTEGER,
            count_last_hour REAL,
            amount_vs_usual REAL,
            share_same_hour REAL,
            latency_ms REAL
        )
    """)
    conn.commit()
    return conn


def log_prediction(conn, purchase, key, features, answer, latency_ms):
    """Insert one scored purchase: what came in, what the model said, and how long it took."""
    conn.execute(
        "INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(purchase["timestamp"]),
            key,
            float(purchase["amount"]),
            answer["fraud_score"],
            int(answer["is_fraud"]),
            int(purchase["is_fraud"]),
            features["new_shop"],
            features["outside_us"],
            features["count_last_hour"],
            features["amount_vs_usual"],
            features["share_same_hour"],
            latency_ms,
        ),
    )
    conn.commit()
