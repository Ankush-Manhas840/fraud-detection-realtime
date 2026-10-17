"""ALL feature functions. Shared by training and live scoring (one code path, no skew)."""


def add_hour(df):
    """Add `hour` (0 to 23) from `timestamp`."""
   
    df["hour"]=df["timestamp"].dt.hour
    return df


def add_outside_us(df):
    """Add `outside_us`: 1 when there is no zip but `merchant_state` has a value (a country name)."""
    df["outside_us"]=(df["zip"].isna()& df["merchant_state"].notna()).astype(int)
    return df


def add_card_history(df):
    
    """Sort by user, card and time, then add `new_shop` and `gap_minutes` from each card's own history."""
    df=df.reset_index(drop=True)
    df=df.sort_values(["user","card","timestamp"])
    df["seen_before"]=df.duplicated(subset=["user","card","merchant_name"])
    df["new_shop"]=(~df["seen_before"]).astype(int)
    df["gap"]=df.groupby(["user","card",])["timestamp"].diff()
    df["gap_minutes"]=df["gap"].dt.total_seconds()/60
    return df
    


def build_features(df):
    """Apply every feature function in order and return the DataFrame."""
    df=add_hour(df)
    df=add_outside_us(df)
    df=add_card_history(df)
    return df
    
