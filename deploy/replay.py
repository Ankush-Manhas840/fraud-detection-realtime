"""Online version of the producer: sends the saved purchases to Kafka forever, one per second.

After the last purchase it waits for the consumer to finish, resets the card memory, and starts again.
"""
import time
from pathlib import Path

import pandas as pd
from confluent_kafka import Producer

from deploy.seed import seed

STREAM = Path(__file__).resolve().parent / "data" / "stream.csv.gz"
SECONDS_BETWEEN = 1.0


def main():
    stream = pd.read_csv(STREAM, parse_dates=["timestamp"])
    producer = Producer({"bootstrap.servers": "localhost:9092"})
    while True:
        for _, purchase in stream.iterrows():
            producer.produce("transactions", value=purchase.to_json(date_format="iso"))
            producer.poll(0)
            time.sleep(SECONDS_BETWEEN)
        producer.flush()
        time.sleep(30)   # let the consumer score the last purchases
        seed()           # fresh memory, so the next round has no duplicates


if __name__ == "__main__":
    main()
