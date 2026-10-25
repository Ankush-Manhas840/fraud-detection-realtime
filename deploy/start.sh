#!/bin/sh
# Starts every part of the pipeline inside one container, in order.
set -e
cd /app

echo "1. Redis"
redis-server --daemonize yes --save "" --appendonly no

echo "2. Kafka (single node, KRaft mode)"
KAFKA_CLUSTER_ID="$(kafka/bin/kafka-storage.sh random-uuid)"
kafka/bin/kafka-storage.sh format --standalone -t "$KAFKA_CLUSTER_ID" -c kafka/config/server.properties
KAFKA_HEAP_OPTS="-Xmx512M -Xms512M" kafka/bin/kafka-server-start.sh -daemon kafka/config/server.properties
until kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --if-not-exists --topic transactions 2>/dev/null; do sleep 2; done

echo "3. Card memory into Redis"
python -m deploy.seed

echo "4. Fraud API"
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 &
until curl -s localhost:8000/health >/dev/null; do sleep 1; done

echo "5. Consumer and producer"
python -m src.streaming.consumer > consumer.log 2>&1 &
python -m deploy.replay > replay.log 2>&1 &

echo "6. Dashboard (public page)"
exec streamlit run dashboard/app.py --server.port 7860 --server.address 0.0.0.0 --server.headless true
