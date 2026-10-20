# Real-Time Fraud Detection System

A small local version of a payment-company fraud pipeline: stream transactions, build live features, score them with a tracked model, explain and monitor every decision.

<p align="center"><img src="docs/project-overview.svg" alt="Project overview: pipeline stages with status, progress by phase, and key findings so far" width="100%"></p>

**Status (Oct 20):** the chosen model (logistic regression on 9 features, 177 real frauds in its top 1,000 alerts on unseen people) is served by a FastAPI app with `/health` and `/predict`, and tested with pytest. `/predict` flags a purchase when its score is at least 0.9862, the level that gives about 1,000 alerts per 600,000 purchases. Next: streaming with Docker, Kafka and Redis. The project moved from PaySim to IBM TabFormer after EDA showed PaySim's users never repeat and its balance columns leak the label ([why](#why-not-paysim)).

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

## EDA findings: TabFormer

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

### Which clues separate fraud from normal purchases

Each clue was compared between fraud and normal purchases. Rates are frauds per 10,000 purchases; the overall rate is about 11.

| Clue | What was found | Use it? |
|---|---|---|
| `outside_us` (no US zip, country name in `merchant_state`) | 391 abroad against 9 at home, **about 45 times riskier**. Under 1% of purchases but about a quarter of all fraud. | Yes |
| `new_shop` (card has never used this shop before) | 155 against 5.5, **about 28 times riskier**. 4% of purchases but over half of all fraud. | Yes |
| `use_chip` | Online 52, chip 8, swipe 5. Online fraud only needs the card number. | Yes |
| `mcc` (type of shop) | Jewellery 608, electronics 562, furniture 442, antiques 312: expensive goods that are easy to resell. Groceries and fuel are very low. | Yes, as a category |
| `gap_minutes` (time since the card's previous purchase) | Middle gap about 2 hours for fraud against 8 hours for normal. A quarter of frauds come within 25 minutes. | Yes |
| `amount` | Middle fraud purchase $70 against $30 for normal, but fraud avoids very large purchases. | Yes |
| `hour` | Highest from 11 am to 2 pm (about 19), lowest from 8 pm to midnight (about 2). Not a night-time pattern: the simulation models fraudsters working regular hours. | Yes |
| `year` | Jumps between 0 and 28 because fraud comes in bursts and there are few people. A model also has to work on future years. | No |

`new_shop` and `gap_minutes` come from each card's own history (rows sorted by user, card and time). In the live system they are exactly what Redis will keep per card.

**Not used as features:** `year`, `user`, `card`, the raw `timestamp`, and `merchant_name` (only used to build `new_shop`).

### Before training

- Split by time, not randomly, because fraud comes in bursts on the same card.
- `mcc` and `use_chip` are categories and need encoding.
- Each card's first purchase has no `gap_minutes`.
- The dataset does not say which time zone timestamps use; training and live scoring must use the same one.
- Judge the model with precision, recall and PR-AUC, not accuracy.

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

- Prepare data (in Python, from the project folder):
  ```python
  from src.data import load_raw, clean, time_split
  from src.features import build_features
  df = build_features(clean(load_raw("data/raw/card_transaction.v1.csv")))      # first 3M rows
  new = build_features(clean(load_raw("data/raw/card_transaction.v1.csv", start=3_000_000)))  # next 3M rows
  ```
- Train: see [`notebooks/03_modeling.ipynb`](notebooks/03_modeling.ipynb) (script version coming in `src/train.py`)
- Start API (from the project folder): `.venv\Scripts\python -m uvicorn src.api.main:app --reload`, then open http://127.0.0.1:8000/docs
- Run tests: `.venv\Scripts\python -m pytest -v`
- Start Docker services (Kafka + Redis): `docker compose up -d`
- Start stream: _TODO_
- Open dashboard: _TODO_

## API

`src/api/main.py` loads `models/model.joblib` once at start-up and reads the threshold from `config/config.yaml`. `src/api/schemas.py` validates every request with Pydantic, so a wrong type returns a 422 error before reaching the model.

`POST /predict` takes one purchase's 9 features (built from the card's history; `gap_minutes` may be empty for a card's first purchase):

| Purchase | Request (shortened) | Response |
|---|---|---|
| Suspicious | abroad, new shop, 4 purchases in the last hour, 12 times the usual amount, unusual hour | `{"fraud_score": 0.9999, "is_fraud": true}` |
| Normal | usual shop and hour, usual amount, a day since the last purchase | `{"fraud_score": 0.0002, "is_fraud": false}` |

`tests/test_api.py` checks that `/health` answers and that the suspicious purchase scores higher than the normal one.

## Results

Analysis in [`notebooks/03_modeling.ipynb`](notebooks/03_modeling.ipynb). Split by time: train on purchases before 25 April 2017 (2.4 million rows, 2,805 frauds), validate on purchases after it (600,000 rows, 616 frauds). Random guessing scores a PR-AUC of about 0.001 and finds about 1 fraud in 1,000 alerts.

All models are logistic regression with `class_weight="balanced"` in a scikit-learn pipeline (scaling for numbers, one-hot encoding for categories).

| Model | Features | PR-AUC | Frauds in top 1,000 alerts | Precision / recall at top 1,000 |
|---|---|---|---|---|
| **4 (chosen)** | model 1 + new_shop_type, count_last_hour, amount_vs_usual, share_same_hour | **0.097** | **199** | 20% / 32% |
| 1 | amount, hour, outside_us, new_shop, gap_minutes | 0.090 | 150 | 15% / 24% |
| 2 | model 1 + use_chip + mcc | 0.075 | 142 | 14% / 23% |
| 3 | model 1 + use_chip | 0.041 | 17 | 2% / 3% |

### Adding a strong feature made the model worse

`use_chip` looked strong in EDA (online about 11 times riskier than swipe), yet adding it cut the frauds in the top 1,000 alerts from 150 to 17. Comparing the two periods showed **drift**:

| Fraud per 10,000 | Train (before Apr 2017) | Validation (after) | New people (after) |
|---|---|---|---|
| Online | 66.4 | **0.0** | **1.5** |
| Chip | 2.6 | 12.5 | 9.7 |
| Swipe | 4.3 | 9.7 | 3.4 |

The model adds up evidence, so "online" alone pushed about 84,000 innocent online purchases from the later period above real frauds and flooded the top alerts. EDA on all years together hid the change. Card use also shifted from mostly swipe (74% before 2017) to mostly chip (69% after).

A second, independent group of 253 people shows the same drop (1.5 per 10,000 after 2017), so it is a real change in the data, not chance. It is the opposite of the real-world trend after the US chip rollout, where fraud moved online, so it is likely a quirk of the simulator. `use_chip` stays out of the model.

### Test on new people

To check that model 1 was not tuned to its 252 people, it was scored on a different slice of the file without retraining: rows 3 million to 6 million, after removing user 252 (whose history crosses the slice border), keeping only purchases after the 25 April 2017 cut-off. That is 253 new people, 599,848 purchases and 459 frauds, prepared by the same `src/data.py` and `src/features.py` functions (checked to reproduce the notebook features exactly).

| | Validation (same people) | New people |
|---|---|---|
| PR-AUC | 0.090 | **0.074** |
| Frauds in top 1,000 alerts | 150 | **142** |
| Precision / recall at top 1,000 | 15% / 24% | **14% / 31%** |
| Random guessing, frauds in top 1,000 | about 1 | about 1 |

A small drop is expected on unseen people; the model generalises.

### Per-card history features and the final choice

Four more features compare each purchase with the same card's earlier purchases only (no future data): first time at this type of shop, purchases in the last hour, amount divided by the card's earlier average, and the share of earlier purchases at this hour.

| On new people (459 frauds) | PR-AUC | Frauds in top 1,000 |
|---|---|---|
| Model 1, logistic regression, 5 features | 0.074 | 142 |
| XGBoost, default depth 6, 100 trees | 0.045 | 74 |
| XGBoost, depth 3, 5 features | 0.116 | 135 |
| **Model 4, logistic regression, 9 features** | 0.088 | **177** |

**Chosen: model 4.** It catches the most fraud in the top 1,000 alerts on unseen people, its score barely drops from validation (0.097) to new people (0.088), and its weights explain every decision. XGBoost with deep trees learned rules specific to the training people; shallower trees fixed most of that, but it still ranked fewer frauds at the very top, where investigators look.

Strongest weights (scaled features): shopping at the card's usual hour pushes the score down the most (−1.40); a new shop (+0.60) and several purchases in the last hour (+0.50) push it up.

## Progress

### Week 1 — Data, imbalance, features
- [x] **Oct 2** — Scaffold repo, download PaySim `[chore: initial project scaffold]`
- [x] **Oct 3** — EDA in `01_eda.ipynb` `[feat: add EDA notebook]` *(done Oct 15: PaySim dropped, TabFormer EDA in `01b_eda_ibm.ipynb`)*
- [x] **Oct 4** — Baseline Logistic Regression with `class_weight` `[feat: add baseline model]`
- [ ] **Oct 5** — Metrics: precision, recall, PR-AUC, confusion matrix in `evaluate.py` `[feat: add evaluation metrics]`
- [x] **Oct 6** — Time-based train/test split (done in the notebook; moving to `data.py` next) `[feat: add time-based split]`
- [ ] **Oct 7** — Velocity features `[feat: add velocity features]`
- [x] **Oct 17** — Feature pipeline in `src/data.py` and `src/features.py` (hour, outside_us, new_shop, gap_minutes); tested on new people
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
- [x] **Oct 16** — FastAPI app with `/health` `[feat: add fastapi app]`
- [x] **Oct 17** — Pydantic schemas `[feat: add request/response schemas]`
- [x] **Oct 18** — `/predict` with model loaded at startup `[feat: add predict endpoint]`
- [ ] ~~**Oct 19** — SHAP reasons in response~~ skipped: logistic regression weights already explain each score; latency logging moves to monitoring `[feat: add reasons and latency]`
- [ ] **Oct 20** — pytest for features `[test: add feature tests]`
- [x] **Oct 21** — API tests with TestClient `[test: add api tests]`
- [ ] **Oct 22** — YAML config + logging cleanup. *Buffer day* `[refactor: config and logging]`
### Week 4 — Streaming and monitoring
- [ ] **Oct 23** — Simple stream: producer → API, in-memory `UserState` `[feat: add simple stream simulator]`
- [ ] **Oct 24** — Docker basics, `docker compose up` for Kafka + Redis `[chore: add docker compose]`
- [ ] **Oct 25** — Kafka topics, producer, consumer concepts `[feat: add kafka producer]`
- [ ] **Oct 26** — Kafka consumer builds features and calls API `[feat: add kafka consumer]`
- [ ] **Oct 27** — Move user state to Redis `[feat: redis feature state]`
- [ ] **Oct 28** — SQLite prediction log `[feat: add prediction logging]`
- [ ] **Oct 29** — Evidently drift report `[feat: add drift monitoring]`
- [ ] **Added** — Dockerfile for the FastAPI app, and add the API to `docker-compose.yml` so API + Kafka + Redis start together `[feat: dockerize api]`
### Final
- [ ] **Oct 30** — Streamlit dashboard `[feat: add live dashboard]`
- [ ] **Oct 31** — Final README, architecture diagram, demo GIF, LinkedIn post `[docs: final README]`

## Future work

- AWS deployment (SageMaker / EC2, Kinesis, Lambda, CloudWatch)
- CI/CD
