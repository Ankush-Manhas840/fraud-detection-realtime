"""Copies predictions.db into dashboard/snapshot.csv so the online dashboard has data. Run after a clean replay."""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

with sqlite3.connect(ROOT / "predictions.db") as conn:
    df = pd.read_sql("SELECT * FROM predictions", conn)
df.to_csv(ROOT / "dashboard" / "snapshot.csv", index=False)
print(f"saved {len(df):,} rows")
