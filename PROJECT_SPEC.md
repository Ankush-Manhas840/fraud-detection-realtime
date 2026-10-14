# PROJECT SPEC — Real-Time Fraud Detection System

> **For the AI assistant reading this file:** Your job is to **scaffold** this project on the user's computer: create the folder, the folder structure, placeholder files with docstrings and `TODO` comments, the config files, and initialise Git. **Do not implement the full ML logic.** The user is building this themselves over October 2026 as a learning project, one feature per day. Follow the "Scaffolding Instructions" section exactly, then stop and report what you created.

---

## 1. What this project is

A small version of the fraud detection systems used by payment companies. Transactions arrive one at a time (a stream). Each transaction is turned into features (e.g. "how many transactions has this user made recently?"), scored by a trained model, and given a decision: approve or flag. Every prediction is logged, model versions are tracked, and data drift is monitored.

**Pipeline:**

```
PaySim data → Stream producer → Kafka topic → Consumer
                                                 │
                                    builds live features (Redis state)
                                                 │
                                                 ▼
                                    FastAPI /predict  ←  model from MLflow registry
                                                 │
                                    score + SHAP reasons + decision
                                                 │
                                    SQLite prediction log → Evidently drift report
                                                 │
                                    Streamlit dashboard
```

**Scope:** Everything runs locally. Cloud deployment (AWS SageMaker / EC2, Kinesis, Lambda, CloudWatch, CI/CD) is **out of scope** for now and will be added later.

---

## 2. Tech stack

| Area | Tool |
|---|---|
| Language | Python 3.10+ |
| Data | pandas, NumPy |
| Models | scikit-learn (LogReg, Isolation Forest), XGBoost, LightGBM |
| Explainability | SHAP |
| Experiment tracking & registry | MLflow |
| API | FastAPI, Pydantic, Uvicorn |
| Streaming | Kafka (via Docker), `confluent-kafka` |
| Online feature state | Redis (via Docker), `redis-py` |
| Prediction log | SQLite (Python `sqlite3`) |
| Drift monitoring | Evidently |
| Dashboard | Streamlit |
| Testing | pytest, FastAPI `TestClient` |
| Config | YAML (`pyyaml`) |
| Containers (local only) | Docker, Docker Compose |

**Dataset (changed Oct 14):** IBM TabFormer synthetic credit card transactions — https://github.com/IBM/TabFormer. PaySim was dropped after EDA (senders almost never repeat, and the balance columns leak the label); see README "Why not PaySim". Sections below that mention PaySim columns are out of date and get updated as each step is reached.

**Original dataset:** PaySim synthetic mobile money transactions — https://www.kaggle.com/datasets/ealaxi/paysim1
Columns: `step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest, isFraud, isFlaggedFraud`. `step` = 1 hour of simulated time. `isFraud` is the label.

---

## 3. Folder structure to create

Project folder name: **`fraud-detection-realtime`**

```
fraud-detection-realtime/
├── README.md
├── PROJECT_SPEC.md            # this file (copy it in)
├── requirements.txt
├── .gitignore
├── config/
│   └── config.yaml
├── data/
│   ├── raw/                   # PaySim CSV goes here (NOT committed)
│   │   └── .gitkeep
│   └── processed/             # feature tables (NOT committed)
│       └── .gitkeep
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_features.ipynb
│   └── 03_modeling.ipynb
├── src/
│   ├── __init__.py
│   ├── config.py              # loads config/config.yaml
│   ├── data.py                # load raw data, time-based train/test split
│   ├── features.py            # ALL feature functions (shared by training and live scoring)
│   ├── train.py               # trains models, logs to MLflow
│   ├── evaluate.py            # metrics, PR-AUC, threshold tuning
│   ├── explain.py             # SHAP helpers
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app: /health, /predict
│   │   └── schemas.py         # Pydantic models
│   ├── streaming/
│   │   ├── __init__.py
│   │   ├── producer.py        # sends transactions to Kafka (or directly to API)
│   │   ├── consumer.py        # reads Kafka, builds live features, calls API
│   │   └── state.py           # per-user recent-transaction state (dict first, Redis later)
│   └── monitoring/
│       ├── __init__.py
│       ├── prediction_log.py  # writes every prediction to SQLite
│       └── drift.py           # Evidently drift report
├── dashboard/
│   └── app.py                 # Streamlit dashboard
├── tests/
│   ├── __init__.py
│   ├── test_features.py
│   └── test_api.py
├── models/                    # saved models (NOT committed)
│   └── .gitkeep
├── reports/                   # drift reports, figures
│   └── .gitkeep
└── docker-compose.yml         # Kafka + Redis for local use (Week 4)
```

---

## 4. File contents for scaffolding

### 4.1 `requirements.txt`
```
pandas
numpy
scikit-learn
xgboost
lightgbm
shap
mlflow
fastapi
uvicorn[standard]
pydantic
pyyaml
requests
confluent-kafka
redis
evidently
streamlit
pytest
httpx
matplotlib
seaborn
jupyter
joblib
```

### 4.2 `.gitignore`
```
# Python
__pycache__/
*.pyc
.venv/
venv/
.env

# Data and models (too large / not for Git)
data/raw/*
data/processed/*
!data/raw/.gitkeep
!data/processed/.gitkeep
models/*
!models/.gitkeep

# MLflow
mlruns/
mlartifacts/

# Logs and DBs
*.log
*.db
*.sqlite

# Notebooks
.ipynb_checkpoints/

# OS / IDE
.DS_Store
Thumbs.db
.vscode/
.idea/
```

### 4.3 `config/config.yaml`
```yaml
data:
  raw_path: data/raw/paysim.csv
  processed_path: data/processed/
  train_end_step: 500        # time-based split: steps <= this go to train
  target: isFraud

features:
  velocity_windows: [1, 6, 24]   # in PaySim steps (hours)

model:
  name: xgboost
  threshold: 0.5               # tuned later on Oct 11
  path: models/model.joblib

mlflow:
  experiment_name: fraud-detection
  tracking_uri: mlruns

api:
  host: 127.0.0.1
  port: 8000

streaming:
  kafka_bootstrap: localhost:9092
  topic: transactions
  redis_host: localhost
  redis_port: 6379
  send_interval_ms: 50

monitoring:
  prediction_db: predictions.db
  drift_report_dir: reports/
```

### 4.4 `docker-compose.yml` (used from Week 4)
Create a compose file with two services:
- **kafka**: a single-node Kafka broker in KRaft mode (no Zookeeper), exposing port `9092` on localhost. Use the official `apache/kafka` image.
- **redis**: `redis:7` image, exposing port `6379`.

Add a comment at the top: `# Local development only. Start with: docker compose up -d`

### 4.5 Python files
Every `.py` file in `src/`, `dashboard/` and `tests/` must contain:
1. A module docstring explaining what the file is for (use the descriptions in the folder tree above).
2. Empty function stubs with docstrings and `raise NotImplementedError` or `pass`, plus a `# TODO (Oct X):` comment matching the roadmap in Section 6.

Required stubs:

- `src/config.py` → `load_config(path="config/config.yaml") -> dict` (**this one may be fully implemented**, it is simple)
- `src/data.py` → `load_raw()`, `time_based_split(df, train_end_step)`
- `src/features.py` → `add_velocity_features(df, windows)`, `add_deviation_features(df)`, `add_balance_error_features(df)`, `build_features(df)`
- `src/train.py` → `train_baseline()`, `train_xgboost()`, `train_lightgbm()`, `train_isolation_forest()`, `main()`
- `src/evaluate.py` → `compute_metrics(y_true, y_score, threshold)`, `tune_threshold(y_true, y_score, cost_fn, cost_fp)`
- `src/explain.py` → `get_explainer(model)`, `top_reasons(explainer, x_row, k=3)`
- `src/api/schemas.py` → Pydantic models `Transaction` (fields matching PaySim input columns) and `PredictionResponse` (`fraud_score: float`, `is_fraud: bool`, `reasons: list[str]`, `model_version: str`, `latency_ms: float`). **These may be fully written.**
- `src/api/main.py` → FastAPI app with a working `GET /health` returning `{"status": "ok"}`, and a stub `POST /predict`.
- `src/streaming/producer.py`, `consumer.py`, `state.py` → stubs with `main()` / class `UserState` with `update()` and `get_features()`
- `src/monitoring/prediction_log.py` → `init_db()`, `log_prediction(...)`
- `src/monitoring/drift.py` → `generate_drift_report(reference_df, current_df, out_path)`
- `dashboard/app.py` → Streamlit app showing a title "Fraud Detection — Live Monitor" and a TODO
- `tests/test_features.py`, `tests/test_api.py` → one placeholder test each that passes, plus a working test for `/health` in `test_api.py`

### 4.6 Notebooks
Create the three notebooks with a single markdown cell containing the notebook's title and goal:
- `01_eda.ipynb` — "Exploratory Data Analysis: fraud rate, fraud by type, amounts over time"
- `02_features.ipynb` — "Feature engineering: velocity, deviation, balance-error features"
- `03_modeling.ipynb` — "Modeling: baseline, XGBoost, LightGBM, Isolation Forest, SHAP"

### 4.7 `README.md`
Include these sections (short, with placeholders where results will go):
1. **Title + one-line description**
2. **Architecture** — copy the pipeline diagram from Section 1
3. **Tech stack** — table from Section 2
4. **Dataset** — PaySim link and note that data is not committed
5. **Setup** — create venv, `pip install -r requirements.txt`, download PaySim CSV into `data/raw/paysim.csv`
6. **How to run** — placeholders: train, start API, start Docker services, start stream, open dashboard
7. **Results** — placeholder table: Model | PR-AUC | Precision | Recall | Threshold
8. **Progress** — the checklist from Section 6 as Markdown checkboxes
9. **Future work** — AWS deployment, CI/CD

---

## 5. Scaffolding instructions (for the AI)

1. Ask the user where to create the project if not already told. Default: their home directory or `Documents/`.
2. Create the folder `fraud-detection-realtime` and every file/folder in Section 3.
3. Fill files as described in Section 4.
4. Copy this `PROJECT_SPEC.md` into the project root.
5. Create a virtual environment: `python -m venv .venv`
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
6. Install requirements: `pip install -r requirements.txt`
7. Run `pytest` and confirm the placeholder tests pass.
8. Initialise Git:
   ```
   git init
   git add .
   git commit -m "chore: initial project scaffold"
   git branch -M main
   ```
9. If the GitHub CLI (`gh`) is installed and logged in, create a **public** repo and push:
   `gh repo create fraud-detection-realtime --public --source=. --push`
   Otherwise, tell the user to create an empty repo named `fraud-detection-realtime` on GitHub and run:
   ```
   git remote add origin https://github.com/<username>/fraud-detection-realtime.git
   git push -u origin main
   ```
10. Report back: the folder path, the file tree, test result, and whether the GitHub push succeeded.

**Do not** download the dataset automatically (Kaggle requires login). Tell the user to download it manually into `data/raw/paysim.csv`.

---

## 6. Daily roadmap (October 2026)

Each day: learn → build → commit and push the same day. Suggested commit message in brackets.

### Week 1 — Data, imbalance, features
- [ ] **Oct 2** — Scaffold repo, download PaySim `[chore: initial project scaffold]`
- [ ] **Oct 3** — EDA in `01_eda.ipynb` `[feat: add EDA notebook]`
- [ ] **Oct 4** — Baseline Logistic Regression with `class_weight` `[feat: add baseline model]`
- [ ] **Oct 5** — Metrics: precision, recall, PR-AUC, confusion matrix in `evaluate.py` `[feat: add evaluation metrics]`
- [ ] **Oct 6** — Time-based train/test split in `data.py` `[feat: add time-based split]`
- [ ] **Oct 7** — Velocity features `[feat: add velocity features]`
- [ ] **Oct 8** — Deviation + balance-error features, all in `features.py` `[feat: add deviation features]`

### Week 2 — Models, explainability, tracking
- [ ] **Oct 9** — XGBoost with `scale_pos_weight` `[feat: add xgboost model]`
- [ ] **Oct 10** — LightGBM + comparison table in README `[feat: add lightgbm and comparison]`
- [ ] **Oct 11** — Cost-based threshold tuning `[feat: add threshold tuning]`
- [ ] **Oct 12** — Isolation Forest comparison `[feat: add isolation forest]`
- [ ] **Oct 13** — SHAP explanations `[feat: add SHAP explanations]`
- [ ] **Oct 14** — MLflow experiment tracking `[feat: add mlflow tracking]`
- [ ] **Oct 15** — MLflow model registry, save best model. *Buffer day* `[feat: register best model]`

### Week 3 — API, tests, clean code
- [ ] **Oct 16** — FastAPI app with `/health` `[feat: add fastapi app]`
- [ ] **Oct 17** — Pydantic schemas `[feat: add request/response schemas]`
- [ ] **Oct 18** — `/predict` with model loaded at startup `[feat: add predict endpoint]`
- [ ] **Oct 19** — SHAP reasons in response, latency logging `[feat: add reasons and latency]`
- [ ] **Oct 20** — pytest for features `[test: add feature tests]`
- [ ] **Oct 21** — API tests with TestClient `[test: add api tests]`
- [ ] **Oct 22** — YAML config + logging cleanup. *Buffer day* `[refactor: config and logging]`

### Week 4 — Streaming and monitoring
- [ ] **Oct 23** — Simple stream: producer → API, in-memory `UserState` `[feat: add simple stream simulator]`
- [ ] **Oct 24** — Docker basics, `docker compose up` for Kafka + Redis `[chore: add docker compose]`
- [ ] **Oct 25** — Kafka topics, producer, consumer concepts `[feat: add kafka producer]`
- [ ] **Oct 26** — Kafka consumer builds features and calls API `[feat: add kafka consumer]`
- [ ] **Oct 27** — Move user state to Redis `[feat: redis feature state]`
- [ ] **Oct 28** — SQLite prediction log `[feat: add prediction logging]`
- [ ] **Oct 29** — Evidently drift report `[feat: add drift monitoring]`

### Final
- [ ] **Oct 30** — Streamlit dashboard `[feat: add live dashboard]`
- [ ] **Oct 31** — Final README, architecture diagram, demo GIF, LinkedIn post `[docs: final README]`

---

## 7. Important rules for this project

1. **One feature-building code path.** Feature logic lives only in `src/features.py` and is reused by both training and live scoring. This prevents training-serving skew.
2. **No random train/test split.** Always split by `step` (time) to avoid leakage.
3. **Never judge models by accuracy.** Use PR-AUC, precision, recall at a chosen threshold.
4. **Never commit data, models, or `mlruns/`.**
5. **Commit and push every day**, with conventional commit messages (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`).

---

## 8. Learning resources

- Fraud Detection Handbook (main reference): https://fraud-detection-handbook.github.io/fraud-detection-handbook/
- Made With ML (ML systems & code quality): https://madewithml.com/
- Google ML Crash Course — Classification: https://developers.google.com/machine-learning/crash-course/classification
- scikit-learn model evaluation: https://scikit-learn.org/stable/modules/model_evaluation.html
- scikit-learn threshold tuning: https://scikit-learn.org/stable/modules/classification_threshold.html
- scikit-learn outlier detection: https://scikit-learn.org/stable/modules/outlier_detection.html
- pandas windowing: https://pandas.pydata.org/docs/user_guide/window.html
- XGBoost Python intro: https://xgboost.readthedocs.io/en/stable/python/python_intro.html
- LightGBM: https://lightgbm.readthedocs.io/
- SHAP: https://shap.readthedocs.io/
- MLflow: https://mlflow.org/docs/latest/
- FastAPI tutorial: https://fastapi.tiangolo.com/tutorial/
- pytest: https://docs.pytest.org/en/stable/getting-started.html
- Docker: https://docs.docker.com/get-started/
- Confluent Kafka 101 (free course): https://developer.confluent.io/
- Redis: https://redis.io/docs/
- Evidently: https://docs.evidentlyai.com/
- Streamlit: https://docs.streamlit.io/get-started
- StatQuest (YouTube) — precision/recall, XGBoost explanations
