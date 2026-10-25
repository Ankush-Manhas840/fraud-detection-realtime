"""Reads purchases from Kafka, builds live features from card memory in Redis, asks the API, prints the decision.

Run src.streaming.warmup once first, so Redis holds every card's history.
"""
import json
import time

import pandas as pd
import requests
from confluent_kafka import Consumer

from src.connections import kafka_config, redis_client
from src.monitoring.prediction_log import init_db, log_prediction
from src.streaming.state import features_from_memory, update_memory, load_bag, save_bag


def main(group_id="fraud-checker", start_at="earliest"):
    # 1. connect to Redis, Kafka and the API
    r = redis_client()
    consumer = Consumer({**kafka_config(), "group.id": group_id, "auto.offset.reset": start_at})
    consumer.subscribe(["transactions"])
    session = requests.Session()
    db = init_db()
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
            started = time.perf_counter()
            answer = session.post("http://127.0.0.1:8000/predict", json=features).json()
            latency_ms = (time.perf_counter() - started) * 1000
            update_memory(bag, purchase)
            save_bag(r, key, bag)
            log_prediction(db, purchase, key, features, answer, latency_ms)

            label = "FRAUD" if answer["is_fraud"] else "ok"
            print(f'{purchase["timestamp"]}  card {key:>7}  {purchase["amount"]:>9.2f}  score {answer["fraud_score"]:.3f}  {label}')
    except KeyboardInterrupt:
        print("stopped")
    finally:
        consumer.close()
        db.close()


if __name__ == "__main__":
    main()
