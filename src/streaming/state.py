"""Per-user recent-transaction state (dict first, Redis later)."""
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


class UserState:
    def update(self, txn):
        """Record a new transaction for its user."""
        # TODO (Oct 23): in-memory dict. (Oct 27): move to Redis.
        raise NotImplementedError

    def get_features(self, user):
        """Return live features (e.g. velocity) for the user."""
        # TODO (Oct 23 / Oct 27)
        raise NotImplementedError
