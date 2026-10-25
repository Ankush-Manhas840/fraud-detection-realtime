"""Streamlit dashboard: reads the prediction log and shows how the live system is doing.

Locally it reads predictions.db (live, written by the consumer).
Online (Streamlit Cloud) there is no database, so it reads the saved snapshot dashboard/snapshot.csv.
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))   # so `src` can be imported when Streamlit runs this file

import altair as alt
import pandas as pd
import streamlit as st
import redis
import requests

from src.streaming.state import load_bag

DB_PATH = ROOT / "predictions.db"
SNAPSHOT_PATH = Path(__file__).resolve().parent / "snapshot.csv"

ORANGE, BLACK, GREEN, BROWN, CREAM = "#E8A13A", "#1a1a1a", "#4A6B3A", "#7A4A2A", "#F2E6CF"
BROWN_LIGHT = "#C27A45"

st.set_page_config(page_title="Fraud Monitor", page_icon="🌲", layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@500;700&family=Noto+Sans+JP:wght@700&display=swap');
.title {{ font-family: Oswald, sans-serif; font-weight: 700; font-size: 4.2rem !important; line-height: 1;
          letter-spacing: -0.01em; color: {ORANGE}; margin: 0; }}
.title span {{ font-family: 'Noto Sans JP', sans-serif; }}
.subtitle {{ color: {CREAM}; opacity: .75; margin: .4rem 0 1.6rem; }}
.hero {{ position: relative; border: 3px solid {BLACK}; border-radius: 4px; padding: 2rem 2.4rem;
         background: repeating-linear-gradient(to bottom, {ORANGE} 0 9px, {BLACK} 9px 11px); color: {BLACK}; }}
.hero .inner {{ background: {ORANGE}; display: inline-block; padding: .4rem 1rem; }}
.hero .num {{ font-family: Oswald, sans-serif; font-size: 5rem; font-weight: 700; line-height: 1; }}
.hero .vert {{ position: absolute; right: 1.6rem; top: 1.2rem; writing-mode: vertical-rl;
               font-family: 'Noto Sans JP', sans-serif; font-size: 2.4rem; background: {ORANGE}; }}
.card {{ border: 2px solid #3a3530; border-radius: 4px; padding: 1rem 1.2rem; background: #242220;
         background-image: radial-gradient(#ffffff10 1px, transparent 1px); background-size: 6px 6px; }}
.card .k {{ font-size: .8rem; letter-spacing: .12em; text-transform: uppercase; opacity: .7; }}
.card .v {{ font-family: Oswald, sans-serif; font-size: 2.4rem; color: {ORANGE}; }}
h3 {{ font-family: Oswald, sans-serif !important; color: {ORANGE} !important; letter-spacing: .02em; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=2)
def load_predictions():
    """Live database if it exists, otherwise the saved snapshot."""
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql("SELECT * FROM predictions", conn)
        source = "live database"
    else:
        df = pd.read_csv(SNAPSHOT_PATH)
        source = "saved snapshot of a clean run"
    df["ts"] = pd.to_datetime(df["ts"])
    return df, source


st.markdown('<div class="title">FRAUD <span>詐欺</span></div>', unsafe_allow_html=True)
st.markdown(f'<p class="subtitle">Real-time card fraud detection · Kafka → Redis → FastAPI → SQLite · live pipeline</p>',
            unsafe_allow_html=True)

# Hero: the offline result on people the model never saw
st.markdown("""
<div class="hero"><div class="vert">監視</div>
  <div class="inner"><div class="num">177</div>
  <b>frauds caught in the top 1,000 alerts</b><br>on 253 people the model never saw · random guessing catches about 1</div>
</div>""", unsafe_allow_html=True)
st.write("")

@st.fragment(run_every=3)
def live_section():
    """Re-runs every 3 seconds, so new purchases appear without reloading the page."""
    df, source = load_predictions()
    if df.empty:
        st.info("Starting up: the first purchases arrive in about a minute.")
        return
    st.caption(f"Reading the {source} · refreshes every 3 seconds")
    # Live numbers
    caught = int((df["flagged"] & df["is_fraud"]).sum())
    cols = st.columns(4)
    for col, (k, v) in zip(cols, [
        ("Purchases checked", f"{len(df):,}"),
        ("Alerts raised", f"{int(df['flagged'].sum()):,}"),
        ("Frauds caught", f"{caught} of {int(df['is_fraud'].sum())}"),
        ("Average latency", f"{df['latency_ms'].mean():.1f} ms"),
    ]):
        col.markdown(f'<div class="card"><div class="k">{k}</div><div class="v">{v}</div></div>', unsafe_allow_html=True)

    # Purchases and alerts per hour
    st.markdown("### Purchases per hour")
    hourly = (df.set_index("ts").resample("1h")
              .agg(purchases=("score", "size"), alerts=("flagged", "sum")).reset_index())
    hourly["ok"] = hourly["purchases"] - hourly["alerts"]
    long = hourly.melt("ts", ["ok", "alerts"], var_name="kind", value_name="count")
    chart = alt.Chart(long).mark_bar().encode(
        x=alt.X("ts:T", title=None),
        y=alt.Y("count:Q", stack=True, title=None),
        color=alt.Color("kind:N", scale=alt.Scale(domain=["ok", "alerts"], range=[GREEN, ORANGE]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=["ts:T", "kind:N", "count:Q"],
    ).properties(height=260)
    st.altair_chart(chart, use_container_width=True)

    # Alert feed and reasons
    left, right = st.columns([3, 2])
    alerts = df[df["flagged"] == 1].sort_values("ts", ascending=False)
    with left:
        st.markdown("### Latest alerts")
        st.dataframe(alerts[["ts", "card", "amount", "score", "is_fraud"]].head(50),
                     hide_index=True, use_container_width=True)
    with right:
        st.markdown("### Why was it flagged?")
        if alerts.empty:
            st.info("No alerts yet.")
        else:
            labels = [f"{r.ts:%d %b %H:%M} · card {r.card} · ${r.amount:,.2f}" for r in alerts.itertuples()]
            pick = alerts.iloc[st.selectbox("Pick an alert", range(len(labels)), format_func=labels.__getitem__)]
            st.markdown(f"""
    - **Fraud score:** {pick.score:.3f}
    - **New shop for this card:** {"yes" if pick.new_shop else "no"}
    - **Outside the US:** {"yes" if pick.outside_us else "no"}
    - **Purchases in the last hour:** {pick.count_last_hour:.0f}
    - **Amount compared with usual:** {pick.amount_vs_usual:.1f} times
    - **Share of this card's purchases at this hour:** {pick.share_same_hour:.0%}
    - **Really fraud?** {"yes" if pick.is_fraud else "no"}
    """)



live_section()


# Try it yourself: a visitor builds a purchase for a real card and the real model scores it
st.markdown("### Try it yourself")
st.write("Pick a real card, change the purchase, and the model in the API scores it using that card's memory in Redis.")
try:
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    cards = sorted(k.removeprefix("card:") for k in r.scan_iter("card:*"))
except redis.exceptions.ConnectionError:
    cards = []

if not cards:
    st.info("The live pipeline is not running here, so the model cannot be tried right now.")
else:
    a, b = st.columns([1, 2])
    with a:
        card = st.selectbox("Card", cards, index=0)
        bag = load_bag(r, card)
        usual = bag["total"] / bag["count"] if bag["count"] else 0
        top_hours = sorted(bag["hour_counts"], key=bag["hour_counts"].get, reverse=True)[:3]
        st.markdown(f"""<div class="card"><div class="k">This card's habits</div>
            {bag["count"]:,} past purchases<br>usual amount ${usual:,.2f}<br>
            favourite hours: {", ".join(f"{h}:00" for h in top_hours)}</div>""", unsafe_allow_html=True)
    with b:
        c1, c2 = st.columns(2)
        amount = c1.number_input("Amount ($)", min_value=1.0, value=float(round(usual, 2)) or 50.0, step=10.0)
        hour = c2.slider("Hour of the day", 0, 23, top_hours[0] if top_hours else 12)
        last_hour = c1.slider("Purchases in the last hour", 0, 10, 0)
        gap = c2.slider("Minutes since the last purchase", 1, 2000, 600)
        new_shop = c1.toggle("A shop this card never used")
        new_type = c2.toggle("A kind of shop this card never used")
        abroad = c1.toggle("Outside the US")
        if st.button("Check this purchase", type="primary"):
            features = {
                "amount": amount, "hour": hour, "outside_us": int(abroad),
                "new_shop": int(new_shop), "new_shop_type": int(new_type),
                "gap_minutes": float(gap), "count_last_hour": last_hour,
                "amount_vs_usual": amount / max(abs(usual), 1),
                "share_same_hour": bag["hour_counts"].get(hour, 0) / bag["count"] if bag["count"] else 0,
            }
            try:
                answer = requests.post("http://127.0.0.1:8000/predict", json=features, timeout=5).json()
                if answer["is_fraud"]:
                    verdict, colour = "FRAUD ALERT", ORANGE
                elif answer["fraud_score"] > 0.5:
                    verdict, colour = "Suspicious", BROWN_LIGHT
                else:
                    verdict, colour = "Looks normal", GREEN
                st.markdown(f"""<div class="card"><div class="k">Model says</div>
                    <div class="v" style="color:{colour}">{verdict}</div>
                    fraud score {answer["fraud_score"]:.4f} · alerts start at 0.9862</div>""", unsafe_allow_html=True)
            except requests.exceptions.ConnectionError:
                st.error("The API is not running.")

st.caption("Model: logistic regression, 9 per-card features, alert threshold 0.9862. "
           "Online fraud vanished after 2017 (66 → 1.5 per 10,000), so the chip feature was left out.")
