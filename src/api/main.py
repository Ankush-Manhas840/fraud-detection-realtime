"""FastAPI app: /health and /predict."""
from fastapi import FastAPI

from src.api.schemas import PredictionResponse, Transaction

app = FastAPI(title="Fraud Detection API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict(txn: Transaction):
    """Score one transaction."""
    # TODO (Oct 18-19): load model at startup, build features, score, add SHAP reasons and latency.
    raise NotImplementedError
