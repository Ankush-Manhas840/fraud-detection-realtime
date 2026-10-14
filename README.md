# Real-Time Fraud Detection System

A small local version of a payment-company fraud pipeline: stream transactions, build live features, score them with a tracked model, explain and monitor every decision.

## Architecture

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

## Tech stack

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

## Dataset

[PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1) synthetic mobile money transactions. The data is **not committed**; download it manually (Kaggle login required).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Download the PaySim CSV and save it as `data/raw/paysim.csv`.

## EDA findings

Full analysis in [`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb). The data has 6,362,620 transactions over 743 steps (1 step = 1 hour, about 30 days), with 8,213 frauds.

### 1. Fraud only happens in two transaction types

All 8,213 frauds are `CASH_OUT` (4,116) or `TRANSFER` (4,097). There is no fraud in `PAYMENT`, `CASH_IN` or `DEBIT`. Any fair comparison between fraud and normal transactions has to use only these two types.

### 2. Following the money does not work in PaySim

Fraud is described as "take over an account, transfer the money to another account, then cash out". I checked whether the accounts that receive fraud transfers ever send money on:

- Of 4,097 fraud transfers, only **8** receivers ever appear as a sender anywhere in the data.
- **7** of those 8 sent money *before* they received the fraud money, so it cannot be the stolen money moving on.
- The **1** that sent afterwards moved 18,091 out of 1,282,971 received, in a transaction not marked as fraud.

**Conclusion:** PaySim does not model money moving through a chain of accounts. Features based on an account's history are not useful here, so the model has to judge each transaction from its own row.

### 3. The receiver balance columns leak the answer

In fraud rows the receiver's balance often does not change even though money was sent (`oldbalanceDest == newbalanceDest`):

| Group | Receiver balance unchanged |
|---|---|
| Fraud | 49.8% |
| All normal transactions | 36.4% |
| Normal `CASH_OUT` and `TRANSFER` only | 0.06% |

The first comparison made the pattern look weak. Normal transactions include about 2.15 million payments to merchants (names starting with `M`), whose balances are never recorded and are always 0. With those removed, the gap is hundreds of times larger.

The [dataset page](https://www.kaggle.com/datasets/ealaxi/paysim1) explains why: transactions detected as fraud are **cancelled**, so the balances are not updated, and the balance columns "must not be used" for fraud detection. The pattern is a result of the fraud label, not a sign that comes before it. A real-time system also cannot know the balances after a transaction before scoring it.

**Decision:** the balances after the transaction (`newbalanceOrig`, `newbalanceDest`) are treated as leakage and not used as features. The balances before the transaction are known at scoring time and are checked separately before use.

### Next checks

- Data quality: missing values, duplicates, types, impossible values
- Does fraud empty the account (`amount` equal to `oldbalanceOrg`)?
- `isFlaggedFraud`: the dataset page says it flags transfers over 200,000. How many frauds does it catch?

## How to run

- Train: _TODO_
- Start API: _TODO_
- Start Docker services (Kafka + Redis): `docker compose up -d`
- Start stream: _TODO_
- Open dashboard: _TODO_

## Results

| Model | PR-AUC | Precision | Recall | Threshold |
|---|---|---|---|---|
| _TBD_ | | | | |

## Progress

### Week 1 — Data, imbalance, features
- [x] **Oct 2** — Scaffold repo, download PaySim `[chore: initial project scaffold]`
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

## Future work

- AWS deployment (SageMaker / EC2, Kinesis, Lambda, CloudWatch)
- CI/CD
