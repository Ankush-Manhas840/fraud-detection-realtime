"""Streamlit dashboard: reads the prediction log and shows how the live system is doing.

Locally it reads predictions.db (live, written by the consumer).
Online (Streamlit Cloud) there is no database, so it reads the saved snapshot dashboard/snapshot.csv.
"""
import sqlite3
import threading
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))   # so `src` can be imported when Streamlit runs this file

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import redis
import requests

from src.connections import load_secrets, redis_client
from src.streaming.state import load_bag

DB_PATH = ROOT / "predictions.db"
SNAPSHOT_PATH = Path(__file__).resolve().parent / "snapshot.csv"

PINK, INK, YELLOW, CYAN, PAPER, RED = "#E8487F", "#0A080C", "#F8D23C", "#56CDEE", "#F6EEDB", "#E2383C"
HERO_HTML = Path(__file__).resolve().parent / "hero.html"

st.set_page_config(page_title="Fraud Monitor", page_icon="🌲", layout="wide")


@st.cache_resource
def start_pipeline():
    """Online only: start the API, the consumer and the producer as background threads, once per server.

    Kafka (Aiven) and Redis (Redis Cloud) run as cloud services; everything else runs inside this app.
    """
    import uvicorn
    from deploy.replay import main as replay
    from deploy.seed import seed
    from src.streaming.consumer import main as consume

    server = uvicorn.Server(uvicorn.Config("src.api.main:app", host="127.0.0.1", port=8000, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.2)
    seed()   # fresh card memory and an empty log, so a restart never counts purchases twice
    # a new consumer group that starts at the newest message, so old messages from before a restart are skipped
    group = f"web-{int(time.time())}"
    threading.Thread(target=consume, args=(group, "latest"), daemon=True).start()
    time.sleep(15)   # give the consumer time to join before purchases start
    threading.Thread(target=replay, daemon=True).start()
    return True


if load_secrets() is not None:
    with st.spinner("Starting the pipeline: API, Kafka consumer and producer..."):
        start_pipeline()
elif not DB_PATH.exists():
    try:
        sections = list(st.secrets.keys())
    except Exception as error:
        sections = f"could not read secrets: {type(error).__name__}"
    st.warning(f"Cloud connection details not found, so the pipeline is not running. Secret sections seen: {sections}")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Space+Grotesk:wght@400;500;700&display=swap');
.stApp {{ background-color: #1a1226; background-image: radial-gradient(rgba(255,255,255,.06) 1.2px, transparent 1.5px); background-size: 9px 9px; }}
html, body, .stApp, .stMarkdown, p, li, label {{ font-family: 'Space Grotesk', sans-serif; }}
h3 {{ font-family: 'Dela Gothic One', sans-serif !important; font-weight: 400 !important; color: {PAPER} !important;
     display: inline-block; background: {INK}; padding: .2rem 1rem .35rem !important; transform: rotate(-1.2deg);
     box-shadow: 5px 5px 0 {YELLOW}; margin: 1.6rem 0 1rem !important; }}
.card {{ border: 4px solid {INK}; padding: 1rem 1.2rem; background: #221b2c; color: {PAPER}; box-shadow: 7px 7px 0 {PINK};
         background-image: radial-gradient(rgba(86,205,238,.14) 1.2px, transparent 1.5px); background-size: 8px 8px; }}
.card .k {{ font-size: .78rem; letter-spacing: .12em; text-transform: uppercase; color: {CYAN}; font-weight: 700; }}
.card .v {{ font-family: 'Dela Gothic One', sans-serif; font-size: 2.3rem; line-height: 1.15; color: {YELLOW};
            -webkit-text-stroke: 1px {INK}; }}
[data-testid="stDataFrame"] {{ border: 4px solid {INK}; box-shadow: 7px 7px 0 {CYAN}; }}
.stButton > button {{ background: {YELLOW} !important; color: {INK} !important; border: 3px solid {INK} !important; border-radius: 0 !important;
                      font-weight: 700 !important; box-shadow: 5px 5px 0 {PINK}; transition: transform .08s ease-out, box-shadow .08s ease-out; }}
.stButton > button:hover {{ transform: translate(-2px,-2px); box-shadow: 7px 7px 0 {PINK}; }}
.stButton > button:active {{ transform: translate(4px,4px); box-shadow: 1px 1px 0 {PINK}; }}
.foot {{ color: #b9adc2; font-size: .85rem; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=2)
def load_predictions():
    """Live database if it exists, otherwise the saved snapshot."""
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql("SELECT * FROM predictions", conn)
        source = "live database"
    elif SNAPSHOT_PATH.exists():
        df = pd.read_csv(SNAPSHOT_PATH)
        source = "saved snapshot of a clean run"
    else:
        return pd.DataFrame(columns=["ts", "card", "amount", "score", "flagged", "is_fraud", "latency_ms"]), "nothing yet"
    df["ts"] = pd.to_datetime(df["ts"])
    return df, source


# Hero: comic panel with the fraud kaiju (same drawing as the portfolio), the title and the headline result
components.html(HERO_HTML.read_text(encoding="utf-8"), height=430)

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
        color=alt.Color("kind:N", scale=alt.Scale(domain=["ok", "alerts"], range=[CYAN, PINK]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=["ts:T", "kind:N", "count:Q"],
    ).properties(height=260)
    st.altair_chart(chart, width="stretch")

    # Alert feed and reasons
    left, right = st.columns([3, 2])
    alerts = df[df["flagged"] == 1].sort_values("ts", ascending=False)
    with left:
        st.markdown("### Latest alerts")
        st.dataframe(alerts[["ts", "card", "amount", "score", "is_fraud"]].head(50),
                     hide_index=True, width="stretch")
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
    r = redis_client()
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
                    verdict, colour = "FRAUD ALERT", RED
                elif answer["fraud_score"] > 0.5:
                    verdict, colour = "Suspicious", YELLOW
                else:
                    verdict, colour = "Looks normal", CYAN
                st.markdown(f"""<div class="card"><div class="k">Model says</div>
                    <div class="v" style="color:{colour}">{verdict}</div>
                    fraud score {answer["fraud_score"]:.4f} · alerts start at 0.9862</div>""", unsafe_allow_html=True)
            except requests.exceptions.ConnectionError:
                st.error("The API is not running.")

st.caption("Model: logistic regression, 9 per-card features, alert threshold 0.9862. "
           "Online fraud vanished after 2017 (66 → 1.5 per 10,000), so the chip feature was left out.")
