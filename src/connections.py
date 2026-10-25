"""Where Kafka and Redis live.

Online (Streamlit Cloud's Secrets box), or on the laptop with USE_CLOUD=1 (reads secrets/secrets.toml):
connect to the cloud services, Aiven Kafka and Redis Cloud. Otherwise connect to the local Docker services.
"""
import os
import tempfile
import tomllib
from pathlib import Path

import redis

from src.config import ROOT

SECRETS_FILE = ROOT / "secrets" / "secrets.toml"


def load_secrets():
    """Return the secrets as a dict, or None when running against local Docker."""
    if os.environ.get("USE_CLOUD") == "1" and SECRETS_FILE.exists():
        with open(SECRETS_FILE, "rb") as f:
            return tomllib.load(f)
    try:
        import streamlit as st
        if "kafka" in st.secrets:
            return {"kafka": dict(st.secrets["kafka"]), "redis": dict(st.secrets["redis"])}
    except Exception:
        pass
    return None


def kafka_config():
    """Settings for confluent_kafka Producer / Consumer."""
    secrets = load_secrets()
    if secrets is None:
        return {"bootstrap.servers": "localhost:9092"}
    k = secrets["kafka"]
    ca_path = Path(tempfile.gettempdir()) / "aiven-ca.pem"
    ca_path.write_text(k["ca_cert"].strip() + "\n")
    return {
        "bootstrap.servers": k["bootstrap"],
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "SCRAM-SHA-256",
        "sasl.username": k["username"],
        "sasl.password": k["password"],
        "ssl.ca.location": str(ca_path),
    }


def redis_client():
    """A Redis connection that returns text (not bytes)."""
    secrets = load_secrets()
    if secrets is None:
        return redis.Redis(host="localhost", port=6379, decode_responses=True)
    host, port = secrets["redis"]["endpoint"].rsplit(":", 1)
    return redis.Redis(host=host, port=int(port), password=secrets["redis"]["password"], decode_responses=True)
