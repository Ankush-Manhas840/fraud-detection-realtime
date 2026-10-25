"""Per-card memory for live features, kept in a Python dict or in Redis."""
import json

import pandas as pd


def empty_card_memory():
    return {
        "shops": set(),
        "shop_types": set(),
        "last_time": None,
        "recent_times": [],
        "total": 0,
        "count": 0,
        "hour_counts": {},
    }


def features_from_memory(bag, purchase):
    features = {}
    features["amount"] = purchase["amount"]
    features["hour"] = purchase["timestamp"].hour
    features["outside_us"] = int(pd.isna(purchase["zip"]) and pd.notna(purchase["merchant_state"]))

    if purchase["merchant_name"] not in bag["shops"]:
        features["new_shop"] = 1
    else:
        features["new_shop"] = 0

    if bag["last_time"] is None:
        features["gap_minutes"] = None
    else:
        features["gap_minutes"] = (purchase["timestamp"] - bag["last_time"]).total_seconds() / 60

    one_hour_ago = purchase["timestamp"] - pd.Timedelta(hours=1)
    count = 0
    for t in bag["recent_times"]:
        if t > one_hour_ago:
            count = count + 1
    features["count_last_hour"] = count

    if bag["count"] == 0:
        features["amount_vs_usual"] = 1
    else:
        usual = bag["total"] / bag["count"]
        features["amount_vs_usual"] = purchase["amount"] / max(abs(usual), 1)

    if bag["count"] == 0:
        features["share_same_hour"] = 0
    else:
        at_this_hour = bag["hour_counts"].get(features["hour"], 0)
        features["share_same_hour"] = at_this_hour / bag["count"]

    if purchase["mcc"] not in bag["shop_types"]:
        features["new_shop_type"] = 1
    else:
        features["new_shop_type"] = 0

    return features


def update_memory(bag, purchase):
    bag["shops"].add(purchase["merchant_name"])
    bag["shop_types"].add(purchase["mcc"])
    bag["last_time"] = purchase["timestamp"]

    one_hour_ago = purchase["timestamp"] - pd.Timedelta(hours=1)
    bag["recent_times"] = [t for t in bag["recent_times"] if t > one_hour_ago]
    bag["recent_times"].append(purchase["timestamp"])

    bag["total"] = bag["total"] + purchase["amount"]
    bag["count"] = bag["count"] + 1

    hour = purchase["timestamp"].hour
    bag["hour_counts"][hour] = bag["hour_counts"].get(hour, 0) + 1


def save_bag(r, key, bag):
    """Store a card's memory in Redis as JSON text (sets become lists, times become text)."""
    text = json.dumps({
        "shops": [int(s) for s in bag["shops"]],
        "shop_types": [int(t) for t in bag["shop_types"]],
        "last_time": None if bag["last_time"] is None else bag["last_time"].isoformat(),
        "recent_times": [t.isoformat() for t in bag["recent_times"]],
        "total": float(bag["total"]),
        "count": int(bag["count"]),
        "hour_counts": bag["hour_counts"],
    })
    r.set(f"card:{key}", text)


def load_bag(r, key):
    """Read a card's memory from Redis, or an empty memory if the card is not stored yet."""
    text = r.get(f"card:{key}")
    if text is None:
        return empty_card_memory()
    d = json.loads(text)
    return {
        "shops": set(d["shops"]),
        "shop_types": set(d["shop_types"]),
        "last_time": None if d["last_time"] is None else pd.Timestamp(d["last_time"]),
        "recent_times": [pd.Timestamp(t) for t in d["recent_times"]],
        "total": d["total"],
        "count": d["count"],
        "hour_counts": {int(h): c for h, c in d["hour_counts"].items()},
    }


