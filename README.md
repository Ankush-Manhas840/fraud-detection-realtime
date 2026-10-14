# Real-Time Fraud Detection System

A small local version of a payment-company fraud pipeline: stream transactions, build live features, score them with a tracked model, explain and monitor every decision.

## Architecture

```
TabFormer data → Stream producer → Kafka topic → Consumer
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

[IBM TabFormer credit card transactions](https://github.com/IBM/TabFormer): realistic **synthetic** card transactions from IBM research ([paper](https://arxiv.org/abs/1910.03033)). 24,386,900 transactions from 2,000 people and 6,139 cards, 1991 to 2020, with 29,757 frauds (about 12 in 10,000).

The data is **not committed**. Download it from the [IBM Box link](https://ibm.box.com/v/tabformer-data), extract `transactions.tgz`, and save `card_transaction.v1.csv` in `data/raw/`.

The file is sorted by user, so loading the first 3 million rows (`nrows=3_000_000`) gives complete histories for about 252 people and fits in 8 GB of RAM (about 460 MB in memory, compared with 3.7 GB for the full file).

### Why not PaySim

The project started on [PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1). EDA in [`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb) showed two problems for a real-time, per-user system:

- **Users do not repeat.** 6,353,307 of 6,362,620 transactions have a different sender, so per-user features (the point of the Redis state) have no history to count.
- **The balance columns leak the label.** Fraud transactions were cancelled, so their balances were never updated (details below).

TabFormer has about 10,860 transactions per person (median), real timestamps and no balance columns.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Download the TabFormer data as described in [Dataset](#dataset) and save it as `data/raw/card_transaction.v1.csv`.

## EDA findings: TabFormer (in progress)

Analysis in [`notebooks/01b_eda_ibm.ipynb`](notebooks/01b_eda_ibm.ipynb), on the first 3,000,000 rows (about 252 people).

### Cleaning

- Column names lowercased, spaces replaced with `_`, `?` removed.
- `amount` stored as text like `$134.09`: removed the `$` and converted to a number.
- `is_fraud` stored as `Yes`/`No`: converted to 1 and 0.
- `year`, `month`, `day` and `time` joined into one `timestamp`. The data covers June 1995 to February 2020. Rows are grouped by user and card, not sorted by time overall, so sorting is needed before building time-window features.

### Data quality

- **Missing values are explained, not errors.**
  - `errors` is empty when the payment had no error.
  - `merchant_state` and `zip` are empty for online purchases, which have no physical shop (377,485 online purchases, compared with 378,407 missing states).
  - `zip` is also empty for purchases in other countries, where `merchant_state` holds the country name (Mexico, Canada, Italy and others).
- **8 duplicate rows**, mostly the same card, shop, amount and minute with the error "Insufficient Balance". They look like a person retrying a declined payment, so they are kept.
- **143,440 negative amounts** (about 5 in 100). They look like refunds: the same amount at the same shop right after a purchase. Fraud among them is about 8 in 10,000, compared with about 11 in 10,000 overall, so refunds are not a fraud signal. Kept.
- **1,921 zero amounts**, 3 of them fraud. Not yet explained.

### Target

- 3,421 frauds in 3,000,000 transactions (about 11 in 10,000). A model that always says "not fraud" would be 99.89% accurate and catch nothing, so the model will be judged on precision, recall and PR-AUC.
- Fraud is spread across 163 of about 252 people, so it is not concentrated in a few users. The `user` and `card` numbers will not be used as features.

### A fraud burst

The first fraud (user 0, card 0, November 2015) is 7 frauds in a row in about one day. Compared with this person's normal purchases (card swiped at the same few local shops, mostly groceries), every fraud was:

- online,
- at a different shop each time, with a different type of shop each time,
- close together in time.

Feature ideas from this: online purchase, a shop the card has never used before, and the number of purchases by the card in the last hour or day.

Because the simulation never blocks a stolen card, fraud comes in bursts. A random train/test split would put parts of the same burst in both sets, so the split will be by time.

### Next checks

- One column at a time: amounts, card use type, shop type (`mcc`), hour of day
- Each feature idea above, compared fairly between fraud and normal transactions
- Purchases outside the US
- Zero amounts

## EDA findings: PaySim (dataset dropped)

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

### 4. Senders almost never repeat

`nameOrig` has 6,353,307 unique values in 6,362,620 rows, so almost every sender appears once. Per-sender history features cannot work, which is the main reason the project moved to TabFormer.

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
- [ ] **Oct 3** — EDA in `01_eda.ipynb` `[feat: add EDA notebook]` *(in progress: PaySim done and dropped, TabFormer EDA in `01b_eda_ibm.ipynb`)*
- [ ] **Oct 4** — Baseline Logistic Regression with `class_weight` `[feat: add baseline model]`
- [ ] **Oct 5** — Metrics: precision, recall, PR-AUC, confusion matrix in `evaluate.py` `[feat: add evaluation metrics]`
- [ ] **Oct 6** — Time-based train/test split in `data.py` `[feat: add time-based split]`
- [ ] **Oct 7** — Velocity features `[feat: add velocity features]`
- [ ] **Oct 8** — Deviation features (amount compared with the card's usual amount, new shop, new type of shop, outside the US), all in `features.py` `[feat: add deviation features]`. *Balance-error features dropped: they leaked the label in PaySim, and TabFormer has no balances.*
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
