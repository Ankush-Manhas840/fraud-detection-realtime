"""Reads purchases from Kafka, builds live features from card memory in Redis, asks the API, prints the decision.

Run src.streaming.warmup once first, so Redis holds every card's history.
"""
import json

import pandas as pd
import redis
import requests
from confluent_kafka import Consumer

from src.streaming.state import features_from_memory, update_memory, load_bag, save_bag


def main():
    # 1. connect to Redis, Kafka and the API
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    consumer = Consumer({
        "bootstrap.servers": "localhost:9092",
        "group.id": "fraud-checker",
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe(["transactions"])
    session = requests.Session()
    print("waiting for purchases...")

    # 2. check purchases as they arrive, forever (stop with Ctrl + C)
    try:
        while True:
            message = consumer.poll(1)
            if message is None:
                continue
            purchase = json.loads(message.value())
            purchase["timestamp"] = pd.Timestamp(purchase["timestamp"])

            key = f'{purchase["user"]}-{purchase["card"]}'
            bag = load_bag(r, key)
            features = features_from_memory(bag, purchase)
            answer = session.post("http://127.0.0.1:8000/predict", json=features).json()
            update_memory(bag, purchase)
            save_bag(r, key, bag)

            label = "FRAUD" if answer["is_fraud"] else "ok"
            print(f'{purchase["timestamp"]}  card {key:>7}  {purchase["amount"]:>9.2f}  score {answer["fraud_score"]:.3f}  {label}')
    except KeyboardInterrupt:
        print("stopped")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
