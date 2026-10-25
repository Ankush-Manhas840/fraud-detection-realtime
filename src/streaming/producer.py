"""Sends purchases to Kafka one by one, in time order, like a live payment stream."""
import time

import pandas as pd
from confluent_kafka import Producer

from src.data import load_raw, clean, time_split

START = 211000      # first purchase to send (purchases before this were already sent)
COUNT = 1000        # how many purchases to send
COLUMNS = ["user", "card", "timestamp", "amount", "merchant_name", "mcc",
           "merchant_city", "merchant_state", "zip", "is_fraud"]


def main():
    # 1. load the new people, in time order, and keep only purchases after the cut-off
    new = clean(load_raw("data/raw/card_transaction.v1.csv", start=3_000_000))                   # load_raw(...) and clean(...), starting at row 3,000,000
    new= new[new["user"] > 252].sort_values("timestamp")                         # keep users above 252, sorted by timestamp
    cutoff = pd.Timestamp("2017-04-25 21:24:36")
    history, stream = time_split(new,cutoff)           # your time_split

    # 2. connect to Kafka
    producer =Producer({"bootstrap.servers": "localhost:9092"})                    # Producer({...}) at localhost:9092

    # 3. send each purchase
    for _, purchase in stream.iloc[START:START + COUNT].iterrows():
        text = purchase[COLUMNS].to_json(date_format="iso")                     # the purchase's COLUMNS as JSON text, with ISO dates
        producer.produce("transactions", value=text)
        producer.poll(0)
        time.sleep(0.05)               # wait 50 milliseconds, so it looks like a live stream

    producer.flush()
    print(f"sent {COUNT} purchases")


if __name__ == "__main__":
    main()