"""
02_feature_engineering.py - Feature Engineering & Dataset Preparation
Mining Process Quality Prediction Project
"""

import pandas as pd
import numpy as np
import warnings
import os
import json

warnings.filterwarnings('ignore')

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH  = os.path.join(BASE_DIR, "data", "MiningProcess_Flotation_Plant_Database.csv")
OUT_DIR    = os.path.join(BASE_DIR, "outputs", "results")
os.makedirs(OUT_DIR, exist_ok=True)

TARGET   = '% Silica Concentrate'
IRON_COL = '% Iron Concentrate'

print("=" * 60)
print("  MINING QUALITY PREDICTION — FEATURE ENGINEERING")
print("=" * 60)

# ── Load ───────────────────────────────────────────────────────────────────────
print("\n[1/5] Loading data...")
df = pd.read_csv(DATA_PATH, sep=',', decimal=',')
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d %H:%M:%S')
df = df.sort_values('date').reset_index(drop=True)
df.columns = [c.strip() for c in df.columns]
df = df.set_index('date')
print(f"      Loaded {df.shape[0]:,} rows × {df.shape[1]} cols")

# ── Resample to 1-minute ───────────────────────────────────────────────────────
print("\n[2/5] Resampling to 1-minute intervals...")
df_1min = df.resample('1min').mean()
df_1min = df_1min.dropna(subset=[TARGET])
print(f"      1-minute dataset: {df_1min.shape[0]:,} rows")

# ── Resample to 1-hour ────────────────────────────────────────────────────────
print("\n[3/5] Resampling to 1-hour intervals...")
df_1h = df.resample('1h').mean()
df_1h = df_1h.dropna(subset=[TARGET])
print(f"      1-hour dataset  : {df_1h.shape[0]:,} rows")

def add_features(data, freq_label='1h'):
    """Add lag and rolling features for time-series prediction."""
    d = data.copy()

    # Process feature columns (exclude targets)
    feature_cols = [c for c in d.columns if c not in [TARGET, IRON_COL]]

    if freq_label == '1h':
        lags = [1, 2, 3, 4, 6, 8, 12, 24]
        windows = [3, 6, 12, 24]
    else:  # 1min
        lags = [1, 5, 10, 30, 60]
        windows = [5, 15, 30, 60]

    # Lag features for target
    for lag in lags:
        d[f'target_lag_{lag}'] = d[TARGET].shift(lag)

    # Rolling stats on target
    for w in windows:
        d[f'target_roll_mean_{w}'] = d[TARGET].shift(1).rolling(w).mean()
        d[f'target_roll_std_{w}']  = d[TARGET].shift(1).rolling(w).std()

    # Key process variable lags (top influencers)
    key_cols = [c for c in feature_cols if 'Airflow' in c or 'Level' in c or 'Flotation' in c]
    key_cols = key_cols[:8]  # top 8 process vars
    for col in key_cols:
        for lag in lags[:4]:
            d[f'{col}_lag_{lag}'] = d[col].shift(lag)

    # Time features
    d['hour']      = d.index.hour
    d['dayofweek'] = d.index.dayofweek
    d['hour_sin']  = np.sin(2 * np.pi * d['hour'] / 24)
    d['hour_cos']  = np.cos(2 * np.pi * d['hour'] / 24)

    # Drop rows with NaN from lags
    d = d.dropna()
    return d

# ── Build feature sets ─────────────────────────────────────────────────────────
print("\n[4/5] Engineering features...")

# Experiment A & C — 1-minute resolution (Q1 and Q3)
print("      Building 1-minute feature set (Q1)...")
df_min_fe = add_features(df_1min, freq_label='1min')
print(f"      Q1 dataset: {df_min_fe.shape[0]:,} rows × {df_min_fe.shape[1]} features")

# Experiment B — 1-hour resolution, multi-step (Q2)
print("      Building 1-hour feature set (Q2)...")
df_h_fe = add_features(df_1h, freq_label='1h')
print(f"      Q2 dataset: {df_h_fe.shape[0]:,} rows × {df_h_fe.shape[1]} features")

# ── Create multi-step targets ──────────────────────────────────────────────────
print("\n[5/5] Creating multi-step targets (1h, 2h, 4h, 8h, 12h ahead)...")
horizons = [1, 2, 4, 8, 12]
df_multi = df_h_fe.copy()
for h in horizons:
    df_multi[f'target_{h}h_ahead'] = df_1h[TARGET].shift(-h)
df_multi = df_multi.dropna()
print(f"      Multi-step dataset: {df_multi.shape[0]:,} rows")

# ── Save processed datasets ────────────────────────────────────────────────────
df_min_fe.to_parquet(os.path.join(OUT_DIR, 'features_1min.parquet'))
df_h_fe.to_parquet(os.path.join(OUT_DIR, 'features_1h.parquet'))
df_multi.to_parquet(os.path.join(OUT_DIR, 'features_multistep.parquet'))

meta = {
    'n_features_1min':  df_min_fe.shape[1],
    'n_rows_1min':      df_min_fe.shape[0],
    'n_features_1h':    df_h_fe.shape[1],
    'n_rows_1h':        df_h_fe.shape[0],
    'n_rows_multistep': df_multi.shape[0],
    'feature_names':    list(df_h_fe.drop(columns=[TARGET, IRON_COL], errors='ignore').columns),
    'horizons':         horizons,
}
with open(os.path.join(OUT_DIR, 'feature_meta.json'), 'w') as f:
    json.dump(meta, f, indent=2)

print("\n✅ Feature engineering complete.")
print(f"   Saved: features_1min.parquet, features_1h.parquet, features_multistep.parquet")
