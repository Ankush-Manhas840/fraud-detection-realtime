"""FastAPI app: /health and /predict."""
from fastapi import FastAPI
import pandas as pd
import joblib
from src.api.schemas import PredictionResponse, Transaction
from src.config import ROOT,load_config
from src.features import FEATURES
app = FastAPI(title="Fraud Detection API")


cfg = load_config()
model = joblib.load(ROOT / cfg["model"]["path"])
THRESHOLD = cfg["model"]["threshold"]

app = FastAPI(title="Fraud Detection API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict(txn: Transaction):
    """Score one purchase."""
    row = pd.DataFrame([txn.model_dump()])[FEATURES]
    row = row.fillna({"gap_minutes": 100000})
    score = float(model.predict_proba(row)[0, 1])
    return PredictionResponse(fraud_score=score, is_fraud=score >= THRESHOLD)