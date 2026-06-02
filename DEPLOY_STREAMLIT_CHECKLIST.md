# Streamlit Cloud Deployment Checklist

Use this checklist to deploy this repository on Streamlit Community Cloud.

## 1. Pre-deploy checks

- [ ] Code is pushed to GitHub.
- [ ] Main app file exists at app.py.
- [ ] requirements.txt includes all runtime dependencies.
- [ ] Model artifacts exist in models/:
  - best_model_xgboost.joblib
  - scaler.joblib
  - feature_columns.json
  - metadata.json
- [ ] Data/results files exist:
  - data/processed_features.csv
  - results/tournament_simulation_results.json
  - results/plots/*.png

## 2. Create the app on Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with GitHub.
3. Click New app.
4. Select:
   - Repository: Code-py-js/Champions_league_predictor
   - Branch: main
   - Main file path: app.py
5. Click Deploy.

## 3. Secrets and environment variables

This dashboard does not require RAPIDAPI_KEY for basic simulation and UI rendering.

Only add secrets if you plan to run API extraction from the deployed app in the future.

If needed, set secrets in Streamlit Cloud app settings, not in .env.

## 4. Expected runtime behavior

- The app should boot and load dashboard UI.
- The Run New Simulation button should execute simulation logic and refresh charts.
- If inactive for some time, free-tier app may sleep and wake on first request.

## 5. Post-deploy smoke tests

- [ ] Home page loads without import errors.
- [ ] KPI cards render values.
- [ ] Visual Diagnostics tabs show images.
- [ ] Data Explorer table renders.
- [ ] CSV download works.
- [ ] Run New Simulation completes successfully.

## 6. Common issues and fixes

1. ModuleNotFoundError (for matplotlib/seaborn)
- Fix: ensure requirements.txt contains matplotlib and seaborn.

2. File not found errors for models or results
- Fix: commit required files in models/, data/, results/.

3. App deploys but simulation fails
- Fix: check app logs in Streamlit Cloud and verify model files + feature columns match simulation code.

## 7. Update and redeploy flow

1. Push changes to main.
2. Streamlit Cloud auto-redeploys.
3. Review deploy logs and run the smoke checks above.
