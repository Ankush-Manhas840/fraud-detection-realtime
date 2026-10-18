"""ALL feature functions. Shared by training and live scoring (one code path, no skew)."""

# Columns the model uses, in order. Chosen in notebooks/03_modeling.ipynb.
FEATURES = [
    "amount", "hour", "outside_us", "new_shop", "gap_minutes",
    "new_shop_type", "count_last_hour", "amount_vs_usual", "share_same_hour",
]


def add_hour(df):
    """Add `hour` (0 to 23) from `timestamp`."""
   
    df["hour"]=df["timestamp"].dt.hour
    return df


def add_outside_us(df):
    """Add `outside_us`: 1 when there is no zip but `merchant_state` has a value (a country name)."""
    df["outside_us"]=(df["zip"].isna()& df["merchant_state"].notna()).astype(int)
    return df


def add_card_history(df):
    """Sort by user, card and time, then add features that compare each purchase with the card's own past."""
    df = df.sort_values(["user", "card", "timestamp"])
    df = df.reset_index(drop=True)
    df["seen_before"]=df.duplicated(subset=["user","card","merchant_name"])
    df["new_shop"]=(~df["seen_before"]).astype(int)
    df["new_shop_type"] = (~df.duplicated(subset=["user", "card", "mcc"])).astype(int)
    df["gap"]=df.groupby(["user","card",])["timestamp"].diff()
    df["gap_minutes"]=df["gap"].dt.total_seconds()/60
    df["count_last_hour"] = df.groupby(["user", "card"]).rolling("60min", on="timestamp")["amount"].count().values - 1
    g = df.groupby(["user", "card"])
    earlier_total = g["amount"].cumsum() - df["amount"]
    earlier_count = g.cumcount()
    usual = earlier_total / earlier_count
    df["amount_vs_usual"] = (df["amount"] / usual.abs().clip(lower=1)).fillna(1)
    same_hour_before = df.groupby(["user", "card", "hour"]).cumcount()
    df["share_same_hour"] = (same_hour_before / earlier_count).fillna(0)
    return df
    


def build_features(df):
    """Apply every feature function in order and return the DataFrame."""
    df=add_hour(df)
    df=add_outside_us(df)
    df=add_card_history(df)
    return df
    
