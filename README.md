# Champions League Predictor (Monte Carlo)

End-to-end ML pipeline to **predict UEFA Champions League match outcomes** and to estimate **tournament winner probabilities** via **Monte Carlo simulation**.

---

## What this project does

1. **Collect historical match data** for Champions League seasons.
2. **Clean and engineer predictive features** using time-ordered team form signals.
3. **Train classification models** to predict match result classes:
   - Draw
   - Home win
   - Away win
4. **Simulate the knockout bracket** many times using the trained model’s `predict_proba()` outputs.
5. **Visualize** results and display them in a **Streamlit dashboard**.

---

## Data collection

### Sources
This repository supports multiple collection paths:

- **API extraction** (stored for future/production use):
  - `run_extraction.py` orchestrates extraction using `src/extraction/api_extractor.py`.
  - Requires `RAPIDAPI_KEY` in `.env`.

- **FBRef web scraping** (historical match ingestion):
  - `src/extraction/scraper.py` implements `FBRefScraper`.
  - Includes randomized delays to reduce the chance of IP blocking.

- **Mock data fallback** (for environments without Mongo/API credentials):
  - `generate_mock_data.py` produces `data/champions_league_matches.json`.
  - `save_mock_data.py` can also seed MongoDB.

### Storage
- Raw match records can be stored in **MongoDB** (`matches` collection) or saved locally as JSON/CSV artifacts under `data/`.

---

## Data cleaning & feature engineering

Feature engineering lives in:
- `src/features/engineer.py`

The pipeline produces a training-ready dataset stored as:
- `data/processed_features.csv`

### Key steps

1. **Chronological ordering**
   - Matches are sorted by the `date` column.
   - This is critical for time-series learning and leakage prevention.

2. **Elo ratings (pre-match, anti-leakage)**
   - The code computes **team Elo ratings before** each match.
   - It records `Home_Elo_Pre` and `Away_Elo_Pre` and only updates Elo **after** recording.
   - This ensures the model never “sees the future” result when estimating pre-match strength.

3. **Rolling momentum (anti-leakage)**
   - Uses rolling 5-match averages for goals scored/conceded.
   - Anti-leakage is enforced with `.shift(1)` so the momentum at match *N* only reflects matches *N-1 … N-5*.
   - Produces:
     - `Home_Rolling_Goals_Scored`
     - `Home_Rolling_Goals_Conceded`
     - `Away_Rolling_Goals_Scored`
     - `Away_Rolling_Goals_Conceded`

4. **Target creation**
   - Classifies match outcomes into a 3-class label `Target`:
     - Home win → `1`
     - Draw → `0`
     - Away win → `2`

5. **Cleaning and selection**
   - Rows with insufficient rolling history are dropped.
   - The final feature set is exported (CSV and/or MongoDB fallback).

---

## Model training

Model training lives in:
- `src/models/train.py`

It trains and evaluates:
- **Logistic Regression** baseline
- **XGBoost** model with hyperparameter tuning

### How training is done

1. **Time-series split by season**
   - Training seasons: earlier seasons (e.g., 2015–2022/2023)
   - Test season: latest season (e.g., 2023–2024)

2. **Scaling (train-only fit)**
   - `StandardScaler` is fitted only on the training set.
   - The fitted scaler is applied to test data.

3. **XGBoost tuning**
   - Uses `GridSearchCV` with `TimeSeriesSplit`.
   - Scoring uses multi-class log loss.

4. **Evaluation metrics**
   - Multi-class **Log Loss**
   - Multi-class **Brier Score** (via one-hot encoding)

### Saved model artifacts
After training, the project writes:
- `models/best_model_xgboost.joblib`
- `models/scaler.joblib`
- `models/feature_columns.json`
- `models/metadata.json`

---

## Tournament simulation (Monte Carlo)

Simulation lives in:
- `src/simulation/bracket.py`

### Core idea
- The model predicts probabilities for the match outcome classes using `predict_proba()`.
- Each simulated match samples an outcome from those probabilities.
- The bracket advances (Round of 16 → Quarterfinal → Semifinal → Final → Champion).
- Team strength signals (Elo-like rating and rolling goal signals) are updated dynamically within each simulation iteration.

### Outputs
The simulator writes:
- `results/tournament_simulation_results.json`

The JSON includes per-team probabilities for stages (when available), including:
- `probabilities['champions']`
- `probabilities['finalists']`
- `probabilities['semifinalists']`
- `probabilities['quarterfinalists']`

---

## Visualization & dashboard

### Static visual reports
- `src/visualization/reports.py` generates PNG plots into:
  - `results/plots/`

Plots include:
- Championship probability bar chart
- Progression heatmap
- Drop-off analysis
- Top contenders comparison

### Streamlit app
- `app.py` loads:
  - `results/tournament_simulation_results.json`
  - `results/plots/*.png`

The dashboard:
- Lets you run the simulation again via a slider-controlled number of iterations.
- Displays probabilities and plots.

---

## How to run (typical workflow)

### 1) Prepare data
- If using mock data:
  - `python generate_mock_data.py`

### 2) Engineer features
- `src/features/engineer.py` produces `data/processed_features.csv`

### 3) Train models
- `src/models/train.py` creates `models/*.joblib`

### 4) Run a simulation
- `src/simulation/bracket.py` writes `results/tournament_simulation_results.json`

### 5) Start the dashboard
- `streamlit run app.py`

---

## Project structure

```text
champions_league_predictor/
├── data/
├── models/
├── results/
├── src/
│   ├── extraction/      # API + FBRef scraping
│   ├── features/       # Cleaning + feature engineering (Elo, rolling)
│   ├── models/         # Training (LogReg + XGBoost)
│   ├── simulation/     # Monte Carlo bracket simulation
│   └── visualization/  # Static plots
├── app.py               # Streamlit dashboard
└── run_extraction.py   # Orchestrates API extraction (optional)
```

---

## Notes
- Feature engineering is built to prevent data leakage (pre-match Elo + rolling averages shifted by 1).
- Simulation stage probabilities are derived from counters collected across Monte Carlo iterations and normalized by `num_simulations`.

