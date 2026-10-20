from pydantic import BaseModel


class Transaction(BaseModel):
    amount:float
    hour :int
    outside_us:int
    new_shop:int
    gap_minutes:float | None=None
    new_shop_type:int
    count_last_hour:float
    amount_vs_usual:float
    share_same_hour:float


class PredictionResponse(BaseModel):
    fraud_score: float
    is_fraud: bool
   