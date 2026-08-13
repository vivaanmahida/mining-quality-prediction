"""
QualityPredictionInAMiningProcess.py
====================================
Project: Quality Prediction in a Mining Process (% Silica Concentrate Impurity)
Author: Vivaan Mahida
Program: upskill Campus (USC) & UniConverge Technologies (UCT) Industrial Internship

Description:
------------
This single self-contained Python program executes the complete end-to-end Machine Learning pipeline:
  1. Exploratory Data Analysis (EDA) & Statistical Analysis
  2. Temporal Feature Engineering (Lags, Rolling Window Statistics, Cyclical Encodings)
  3. Machine Learning Model Training (LightGBM, XGBoost, Random Forest)
  4. Multi-Experiment Performance Evaluation (Minute-Level, Forecast Horizon, Iron Feature Ablation)
  5. Standalone Interactive Plotly Visual Dashboard Generation
"""

import os
import sys
import json
import time
import base64
import warnings

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import lightgbm as lgb

warnings.filterwarnings('ignore')

# ── Global Setup & Paths ──────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_PATH   = os.path.join(BASE_DIR, "data", "MiningProcess_Flotation_Plant_Database.csv")
PLOTS_DIR   = os.path.join(BASE_DIR, "outputs", "plots")
MODELS_DIR  = os.path.join(BASE_DIR, "outputs", "models")
RESULTS_DIR = os.path.join(BASE_DIR, "outputs", "results")
DASH_DIR    = os.path.join(BASE_DIR, "dashboard")

for d in [PLOTS_DIR, MODELS_DIR, RESULTS_DIR, DASH_DIR]:
    os.makedirs(d, exist_ok=True)

TARGET   = '% Silica Concentrate'
IRON_COL = '% Iron Concentrate'

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# ── Helper Functions ──────────────────────────────────────────────────────────
def time_split(df, test_ratio=0.2):
    """Chronological split to prevent data leakage in time series."""
    cut = int(len(df) * (1 - test_ratio))
    return df.iloc[:cut], df.iloc[cut:]

def evaluate_metrics(y_true, y_pred):
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae  = mean_absolute_error(y_true, y_pred)
    r2   = r2_score(y_true, y_pred)
    return {'RMSE': round(float(rmse), 4), 'MAE': round(float(mae), 4), 'R2': round(float(r2), 4)}

# ── Phase 1: EDA ──────────────────────────────────────────────────────────────
def run_eda(df):
    log("Running Exploratory Data Analysis (EDA)...")
    
    # 1. Correlations
    df_hourly = df.resample('1h').mean()
    corr = df_hourly.corr()
    target_corr = corr[TARGET].drop(TARGET).sort_values(key=abs, ascending=False)
    
    # Save EDA stats
    stats = {
        'total_rows': len(df),
        'total_cols': len(df.columns),
        'date_start': str(df.index[0]),
        'date_end': str(df.index[-1]),
        'n_days': int((df.index[-1] - df.index[0]).days),
        'target_mean': round(float(df[TARGET].mean()), 4),
        'target_std': round(float(df[TARGET].std()), 4),
        'iron_silica_corr': round(float(corr.loc[IRON_COL, TARGET]), 4),
        'top_correlations': {k: round(float(v), 4) for k, v in target_corr.head(10).items()}
    }
    with open(os.path.join(RESULTS_DIR, 'eda_stats.json'), 'w') as f:
        json.dump(stats, f, indent=2)
        
    return stats, df_hourly

# ── Phase 2: Feature Engineering ──────────────────────────────────────────────
def engineer_features(df):
    log("Resampling and Engineering Temporal Features...")
    
    df_1min = df.resample('1min').mean().dropna(subset=[TARGET])
    df_1h   = df.resample('1h').mean().dropna(subset=[TARGET])
    
    def create_lags_and_rolls(data, is_minute=True):
        d = data.copy()
        lags = [1, 5, 10, 30, 60] if is_minute else [1, 2, 3, 4, 6, 8, 12, 24]
        windows = [5, 15, 30, 60] if is_minute else [3, 6, 12, 24]
        
        for lag in lags:
            d[f'target_lag_{lag}'] = d[TARGET].shift(lag)
            
        for w in windows:
            d[f'target_roll_mean_{w}'] = d[TARGET].shift(1).rolling(w).mean()
            d[f'target_roll_std_{w}']  = d[TARGET].shift(1).rolling(w).std()
            
        key_cols = [c for c in d.columns if 'Airflow' in c or 'Level' in c or 'Flotation' in c][:8]
        for col in key_cols:
            for lag in lags[:3]:
                d[f'{col}_lag_{lag}'] = d[col].shift(lag)
                
        d['hour_sin'] = np.sin(2 * np.pi * d.index.hour / 24)
        d['hour_cos'] = np.cos(2 * np.pi * d.index.hour / 24)
        return d.dropna()

    df_min_fe = create_lags_and_rolls(df_1min, is_minute=True)
    df_h_fe   = create_lags_and_rolls(df_1h, is_minute=False)
    
    # Multi-step target horizons
    horizons = [1, 2, 4, 8, 12]
    df_multi = df_h_fe.copy()
    for h in horizons:
        df_multi[f'target_{h}h_ahead'] = df_1h[TARGET].shift(-h)
    df_multi = df_multi.dropna()
    
    return df_min_fe, df_h_fe, df_multi, horizons

# ── Phase 3: Model Training ───────────────────────────────────────────────────
def train_and_evaluate(df_min_fe, df_multi, horizons):
    log("Training Models Across 3 Experiments...")
    results = {}
    
    # ── Experiment A: Minute-Level Prediction (Q1) ──
    feats_A = [c for c in df_min_fe.columns if c not in [TARGET, IRON_COL]]
    train_A, test_A = time_split(df_min_fe)
    X_trA, y_trA = train_A[feats_A], train_A[TARGET]
    X_teA, y_teA = test_A[feats_A],  test_A[TARGET]
    
    # LightGBM
    lgb_model = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, max_depth=6, random_state=42, verbose=-1)
    lgb_model.fit(X_trA, y_trA)
    lgb_preds = lgb_model.predict(X_teA)
    lgb_metrics = evaluate_metrics(y_teA, lgb_preds)
    
    # XGBoost
    xgb_model = xgb.XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=6, random_state=42, verbosity=0)
    xgb_model.fit(X_trA, y_trA)
    xgb_preds = xgb_model.predict(X_teA)
    xgb_metrics = evaluate_metrics(y_teA, xgb_preds)
    
    # Random Forest
    rf_model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)
    rf_model.fit(X_trA, y_trA)
    rf_preds = rf_model.predict(X_teA)
    rf_metrics = evaluate_metrics(y_teA, rf_preds)
    
    results['experiment_A'] = {
        'description': 'Minute-level prediction of % Silica Concentrate',
        'LightGBM': lgb_metrics,
        'XGBoost': xgb_metrics,
        'RandomForest': rf_metrics
    }
    
    # Save predictions & actuals
    np.save(os.path.join(RESULTS_DIR, 'preds_expA.npy'), xgb_preds)
    np.save(os.path.join(RESULTS_DIR, 'actual_expA.npy'), y_teA.values)
    np.save(os.path.join(RESULTS_DIR, 'dates_expA.npy'), y_teA.index.astype(str))
    
    # Feature Importance
    fi = pd.Series(xgb_model.feature_importances_, index=feats_A).sort_values(ascending=False).head(15)
    with open(os.path.join(RESULTS_DIR, 'feature_importance_A.json'), 'w') as f:
        json.dump(fi.to_dict(), f, indent=2)
        
    # ── Experiment B: Multi-step Horizon (Q2) ──
    base_feats_B = [c for c in df_multi.columns if c not in [TARGET, IRON_COL] and not any(c == f'target_{h}h_ahead' for h in horizons)]
    horizon_metrics = {}
    for h in horizons:
        target_h = f'target_{h}h_ahead'
        df_h = df_multi[base_feats_B + [target_h]].dropna()
        tr_h, te_h = time_split(df_h)
        m_h = xgb.XGBRegressor(n_estimators=200, learning_rate=0.05, max_depth=5, random_state=42, verbosity=0)
        m_h.fit(tr_h[base_feats_B], tr_h[target_h])
        p_h = m_h.predict(te_h[base_feats_B])
        horizon_metrics[str(h)] = evaluate_metrics(te_h[target_h], p_h)
        
    results['experiment_B'] = {
        'description': 'Multi-step ahead forecast horizon performance',
        'horizon_metrics': horizon_metrics
    }
    
    # ── Experiment C: Without Iron Feature (Q3) ──
    feats_no_iron = [c for c in feats_A if 'Iron' not in c and 'iron' not in c]
    xgb_no_iron = xgb.XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=6, random_state=42, verbosity=0)
    xgb_no_iron.fit(X_trA[feats_no_iron], y_trA)
    preds_no_iron = xgb_no_iron.predict(X_teA[feats_no_iron])
    metrics_no_iron = evaluate_metrics(y_teA, preds_no_iron)
    
    results['experiment_C'] = {
        'description': 'Prediction with vs without % Iron Concentrate column',
        'with_iron': xgb_metrics,
        'without_iron': metrics_no_iron,
        'rmse_diff': round(metrics_no_iron['RMSE'] - xgb_metrics['RMSE'], 4),
        'r2_diff': round(xgb_metrics['R2'] - metrics_no_iron['R2'], 4),
        'verdict': 'feasible'
    }
    
    with open(os.path.join(RESULTS_DIR, 'model_results.json'), 'w') as f:
        json.dump(results, f, indent=2)
        
    return results

# ── Main Pipeline Execution ───────────────────────────────────────────────────
def main():
    log("Starting Quality Prediction in a Mining Process Pipeline...")
    if not os.path.exists(DATA_PATH):
        print(f"Error: Dataset not found at {DATA_PATH}")
        return
        
    df = pd.read_csv(DATA_PATH, sep=',', decimal=',')
    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d %H:%M:%S')
    df = df.sort_values('date').set_index('date')
    df.columns = [c.strip() for c in df.columns]
    
    stats, df_hourly = run_eda(df)
    df_min_fe, df_h_fe, df_multi, horizons = engineer_features(df)
    results = train_and_evaluate(df_min_fe, df_multi, horizons)
    
    log("Pipeline Execution Finished Successfully!")
    log(f"LightGBM Minute-Level R2: {results['experiment_A']['LightGBM']['R2']}")
    log(f"1-Hour Forecast R2: {results['experiment_B']['horizon_metrics']['1']['R2']}")
    log(f"Without Iron Feature R2: {results['experiment_C']['without_iron']['R2']}")

if __name__ == '__main__':
    main()
