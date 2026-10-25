# Whole pipeline in one container for Hugging Face Spaces: Kafka + Redis + FastAPI + consumer + producer + Streamlit.
# On the laptop the same pieces run as separate services with docker-compose.yml.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends openjdk-21-jre-headless redis-server curl \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face runs the container as user 1000
RUN useradd -m -u 1000 user
WORKDIR /app

RUN curl -fsSL https://archive.apache.org/dist/kafka/4.1.0/kafka_2.13-4.1.0.tgz | tar xz \
    && mv kafka_2.13-4.1.0 kafka

COPY deploy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY config ./config
COPY models ./models
COPY dashboard ./dashboard
COPY deploy ./deploy
RUN chmod +x deploy/start.sh && chown -R user /app

USER user
EXPOSE 7860
CMD ["deploy/start.sh"]
