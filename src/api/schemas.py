"""Pydantic request/response models for the API."""
from pydantic import BaseModel


class Transaction(BaseModel):
    step: int
    type: str
    amount: float
    nameOrig: str
    oldbalanceOrg: float
    newbalanceOrig: float
    nameDest: str
    oldbalanceDest: float
    newbalanceDest: float


class PredictionResponse(BaseModel):
    fraud_score: float
    is_fraud: bool
    reasons: list[str]
    model_version: str
    latency_ms: float
