# Champions League Predictor

**Lead Data Engineer & ML Architect**: Lead by Salah

An end-to-end Machine Learning pipeline for predicting UEFA Champions League match outcomes and simulating tournament winners using historical data (2015-2024).

## Project Overview

This project builds a comprehensive ML system to:
- Extract historical Champions League match data from FBRef (2015-2024)
- Engineer features including Elo ratings, rolling averages, and Expected Goals (xG)
- Train predictive models (Logistic Regression, XGBoost) to forecast match outcomes
- Simulate the knockout stage 10,000 times to predict tournament winners

## Architecture

```
champions_league_predictor/
├── data/
│   ├── raw/           # Raw scraped/API JSON data
│   ├── processed/     # Cleaned DataFrames ready for modeling
├── src/
│   ├── __init__.py
│   ├── extraction/    # Web scraping (FBRef) & API scripts
│   ├── database/      # MongoDB connection and insertion logic
│   ├── features/      # Data cleaning and feature engineering
│   ├── models/        # XGBoost/Logistic Regression training
│   ├── simulation/    # Monte Carlo bracket simulation
├── tests/             # PyTest suite
├── requirements.txt   # Dependencies
├── main.py            # Orchestration script
└── README.md
```

## Installation

### Prerequisites
- Python 3.10+
- MongoDB (local instance running on port 27017)

### Setup

1. **Clone/Navigate to the workspace:**
   ```bash
   cd champions_league_predictor
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv env
   env\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ensure MongoDB is running:**
   ```bash
   # On Windows with MongoDB installed:
   mongod
   ```

## Usage

### Initialize Pipeline

```bash
python main.py --mode full
```

### Database Connection

Verify MongoDB connection:
```bash
cd champions_league_predictor
python -m pytest tests/test_mongo_client.py -v
```

## Task Breakdown

### Task 1: Project Initialization & DB Setup ✓
- [x] Created workspace structure with SOLID principles
- [x] Implemented `src/database/mongo_client.py`
- [x] MongoDB connection handling with error management
- [x] PyTest suite with 13 passing tests
- [x] Collection creation support

### Task 2: Data Extraction Pipeline
- [ ] Implement `src/extraction/scraper.py`
- [ ] Web scraping from FBRef (2015-2024)
- [ ] Random delays to prevent IP bans
- [ ] Insert raw data into MongoDB

### Task 3: Data Cleaning & Feature Engineering
- [ ] Implement `src/features/engineer.py`
- [ ] Data cleaning and missing value handling
- [ ] Rolling 5-match averages (Goals, xG)
- [ ] Elo rating system implementation
- [ ] Prevent data leakage with .shift()

### Task 4: Model Training & Evaluation
- [ ] Implement `src/models/train.py`
- [ ] Time-series split (2015-2023 train, 2024 test)
- [ ] Logistic Regression baseline
- [ ] XGBoost model training
- [ ] Brier Score and Log Loss evaluation

### Task 5: Tournament Simulation
- [ ] Implement `src/simulation/bracket.py`
- [ ] Monte Carlo 10,000 simulations
- [ ] Knockout stage prediction
- [ ] Tournament winner probabilities

## Dependencies

- `pandas` (2.0.3) - Data manipulation
- `requests` (2.31.0) - HTTP requests
- `beautifulsoup4` (4.12.2) - Web scraping
- `pymongo` (4.4.1) - MongoDB driver
- `scikit-learn` (1.3.0) - ML models and metrics
- `xgboost` (2.0.0) - XGBoost gradient boosting
- `pytest` (7.4.0) - Testing framework
- `joblib` (1.3.1) - Model serialization
- `numpy` (1.24.3) - Numerical computing
- `lxml` (4.9.3) - XML parsing

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run specific module tests:
```bash
pytest tests/test_mongo_client.py -v
```

## MongoDB Setup

### Local MongoDB Connection String
```
mongodb://localhost:27017/
```

### Collections Created
1. `matches` - Historical match data
2. `teams` - Team information and ratings
3. `predictions` - Model predictions

## Contributing

- Follow SOLID principles
- Write PyTest for every module
- Use type hints in function signatures
- Document with docstrings

## Timeline

| Task | Status | Target |
|------|--------|--------|
| Project Initialization & DB Setup | ✓ Complete | Done |
| Data Extraction Pipeline | ⏳ In Progress | Next |
| Data Cleaning & Feature Engineering | ⏳ Pending | TBD |
| Model Training & Evaluation | ⏳ Pending | TBD |
| Tournament Simulation | ⏳ Pending | TBD |

---

**Report**: See task reports in conversation for detailed completion status and metrics.
