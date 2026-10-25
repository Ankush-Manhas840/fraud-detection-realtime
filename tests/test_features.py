"""Tests for src/features.py and the live version in src/streaming/state.py.

A tiny hand-made history for one card, where every feature can be worked out by hand.
"""
import numpy as np
import pandas as pd

from src.features import FEATURES, build_features
from src.streaming.state import empty_card_memory, features_from_memory, update_memory


def tiny_history():
    return pd.DataFrame({
        "user": [0, 0, 0, 0],
        "card": [0, 0, 0, 0],
        "timestamp": pd.to_datetime(["2018-01-01 10:00", "2018-01-01 10:20", "2018-01-01 10:50", "2018-01-02 03:00"]),
        "amount": [10.0, 30.0, 20.0, 200.0],
        "merchant_name": [111, 222, 111, 333],
        "mcc": [5411, 5812, 5411, 5999],
        "zip": [10001.0, 10001.0, 10001.0, np.nan],
        "merchant_state": ["NY", "NY", "NY", "Italy"],
    })


def test_new_shop_and_new_shop_type():
    df = build_features(tiny_history())
    assert df["new_shop"].tolist() == [1, 1, 0, 1]          # shop 111 comes back on the 3rd purchase
    assert df["new_shop_type"].tolist() == [1, 1, 0, 1]


def test_outside_us():
    df = build_features(tiny_history())
    assert df["outside_us"].tolist() == [0, 0, 0, 1]        # no zip + a country name = abroad


def test_gap_and_count_last_hour():
    df = build_features(tiny_history())
    assert np.isnan(df["gap_minutes"][0])                   # first purchase has no earlier one
    assert df["gap_minutes"].tolist()[1:3] == [20.0, 30.0]
    assert df["count_last_hour"].tolist() == [0, 1, 2, 0]   # purchases in the hour BEFORE this one


def test_amount_vs_usual():
    df = build_features(tiny_history())
    # 4th purchase: usual = (10 + 30 + 20) / 3 = 20, so 200 is 10 times usual
    assert df["amount_vs_usual"][3] == 10
    assert df["amount_vs_usual"][0] == 1                    # no history yet


def test_share_same_hour():
    df = build_features(tiny_history())
    # 3rd purchase at 10:xx: both earlier purchases were also at 10:xx
    assert df["share_same_hour"][2] == 1
    assert df["share_same_hour"][3] == 0                    # never bought at 3 AM before


def test_live_features_match_training_features():
    """The live code (card memory) must give the same numbers as the training code (whole table)."""
    history = tiny_history()
    expected = build_features(history.copy())
    bag = empty_card_memory()
    for i, (_, purchase) in enumerate(history.iterrows()):
        live = features_from_memory(bag, purchase)
        for name in FEATURES:
            want = expected[name][i]
            got = live[name]
            if pd.isna(want):
                assert got is None, name
            else:
                assert np.isclose(got, want), (name, i, got, want)
        update_memory(bag, purchase)
