"""Tests for the API."""
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# TODO (Oct 21): tests for /predict.
def test_predict_flags_suspicious_purchase():
    suspicious = {
        "amount": 900, "hour": 3, "outside_us": 1, "new_shop": 1, "gap_minutes": 5,
        "new_shop_type": 1, "count_last_hour": 4, "amount_vs_usual": 12, "share_same_hour": 0,
    }
    normal = {
        "amount": 30, "hour": 6, "outside_us": 0, "new_shop": 0, "gap_minutes": 1400,
        "new_shop_type": 0, "count_last_hour": 0, "amount_vs_usual": 1, "share_same_hour": 0.9,
    }
    r1 = client.post("/predict", json=suspicious)
    r2 = client.post("/predict", json=normal)

    assert r1.status_code == 200
    assert r1.json()["fraud_score"] > r2.json()["fraud_score"]
