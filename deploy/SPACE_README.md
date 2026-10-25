---
title: Real-Time Fraud Detection
emoji: 🌲
colorFrom: yellow
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

Live card-fraud pipeline: purchases stream through **Kafka**, each card's memory lives in **Redis**,
a **FastAPI** service scores them with a logistic regression model, every decision is logged to **SQLite**,
and this **Streamlit** page shows it all as it happens.

Code: https://github.com/Ankush-Manhas840/fraud-detection-realtime
