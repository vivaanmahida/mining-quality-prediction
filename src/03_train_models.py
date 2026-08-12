"""
03_train_models.py - Model Training (3 Experiments)
Mining Process Quality Prediction Project

Experiment A: Minute-level prediction (Q1)
Experiment B: Multi-step ahead prediction (Q2)
Experiment C: Without Iron Concentrate column (Q3)
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
import os
import json
import joblib
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import lightgbm as lgb

warnings.filterwarnings('ignore')

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "outputs", "results")
MODELS_DIR  = os.path.join(BASE_DIR, "outputs", "models")
PLOTS_DIR   = os.path.join(BASE_DIR, "outputs", "plots")
os.makedirs(MODELS_DIR, exist_ok=True)

TARGET   = '% Silica Concentrate'
IRON_COL = '% Iron Concentrate'

# ── Styling ────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    'figure.facecolor': '#0d1117', 'axes.facecolor': '#161b22',
    'axes.edgecolor': '#30363d', 'axes.labelcolor': '#c9d1d9',
    'text.color': '#c9d1d9', 'xtick.color': '#8b949e', 'ytick.color': '#8b949e',
    'grid.color': '#21262d', 'grid.alpha': 0.6,
    'legend.facecolor': '#161b22', 'legend.edgecolor': '#30363d',
    'legend.labelcolor': '#c9d1d9',
})
COLORS = ['#58a6ff', '#f78166', '#3fb950', '#bc8cff', '#ffa657']

def time_split(df, test_ratio=0.2):
    """Chronological train/test split — no data leakage."""
    n = len(df)
    cut = int(n * (1 - test_ratio))
    return df.iloc[:cut], df.iloc[cut:]

def get_metrics(y_true, y_pred):
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae  = mean_absolute_error(y_true, y_pred)
    r2   = r2_score(y_true, y_pred)
    return {'RMSE': round(rmse, 4), 'MAE': round(mae, 4), 'R2': round(r2, 4)}

def train_xgb(X_train, y_train, X_test, y_test, name='xgb'):
    model = xgb.XGBRegressor(
        n_estimators=500, learning_rate=0.05, max_depth=6,
        subsample=0.8, colsample_bytree=0.8,
        early_stopping_rounds=30, eval_metric='rmse',
        random_state=42, n_jobs=-1, verbosity=0
    )
    model.fit(X_train, y_train,
              eval_set=[(X_test, y_test)],
              verbose=False)
    preds = model.predict(X_test)
    return model, preds, get_metrics(y_test, preds)

def train_lgb(X_train, y_train, X_test, y_test, name='lgb'):
    model = lgb.LGBMRegressor(
        n_estimators=500, learning_rate=0.05, max_depth=6,
        num_leaves=63, subsample=0.8, colsample_bytree=0.8,
        random_state=42, n_jobs=-1, verbose=-1
    )
    model.fit(X_train, y_train,
              eval_set=[(X_test, y_test)],
              callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(-1)])
    preds = model.predict(X_test)
    return model, preds, get_metrics(y_test, preds)

def train_rf(X_train, y_train, X_test, y_test):
    model = RandomForestRegressor(
        n_estimators=200, max_depth=10, n_jobs=-1, random_state=42
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    return model, preds, get_metrics(y_test, preds)

print("=" * 60)
print("  MINING QUALITY PREDICTION — MODEL TRAINING")
print("=" * 60)

all_results = {}

# ══════════════════════════════════════════════════════════════
# EXPERIMENT A: Minute-level prediction (Q1)
# ══════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("EXPERIMENT A — Minute-level Prediction (Q1)")
print("─" * 60)

df_min = pd.read_parquet(os.path.join(RESULTS_DIR, 'features_1min.parquet'))
EXCL_A = [TARGET, IRON_COL]
feats_A = [c for c in df_min.columns if c not in EXCL_A]

train_A, test_A = time_split(df_min)
X_trA, y_trA = train_A[feats_A], train_A[TARGET]
X_teA, y_teA = test_A[feats_A],  test_A[TARGET]
print(f"  Train: {len(X_trA):,}  |  Test: {len(X_teA):,}")

print("  Training XGBoost...")
xgb_A, xgb_preds_A, xgb_met_A = train_xgb(X_trA, y_trA, X_teA, y_teA)
print(f"  XGBoost — RMSE:{xgb_met_A['RMSE']:.4f}  MAE:{xgb_met_A['MAE']:.4f}  R²:{xgb_met_A['R2']:.4f}")

print("  Training LightGBM...")
lgb_A, lgb_preds_A, lgb_met_A = train_lgb(X_trA, y_trA, X_teA, y_teA)
print(f"  LightGBM — RMSE:{lgb_met_A['RMSE']:.4f}  MAE:{lgb_met_A['MAE']:.4f}  R²:{lgb_met_A['R2']:.4f}")

print("  Training Random Forest...")
rf_A, rf_preds_A, rf_met_A = train_rf(X_trA, y_trA, X_teA, y_teA)
print(f"  RF      — RMSE:{rf_met_A['RMSE']:.4f}  MAE:{rf_met_A['MAE']:.4f}  R²:{rf_met_A['R2']:.4f}")

all_results['experiment_A'] = {
    'description': 'Minute-level prediction of % Silica Concentrate',
    'XGBoost': xgb_met_A, 'LightGBM': lgb_met_A, 'RandomForest': rf_met_A
}

# Save best model (XGBoost) + predictions
joblib.dump(xgb_A, os.path.join(MODELS_DIR, 'xgb_expA.pkl'))
np.save(os.path.join(RESULTS_DIR, 'preds_expA.npy'), xgb_preds_A)
np.save(os.path.join(RESULTS_DIR, 'actual_expA.npy'), y_teA.values)
np.save(os.path.join(RESULTS_DIR, 'dates_expA.npy'), y_teA.index.astype(str))

# Feature importance
fi_A = pd.Series(xgb_A.feature_importances_, index=feats_A).sort_values(ascending=False)
fi_A.head(20).to_json(os.path.join(RESULTS_DIR, 'feature_importance_A.json'))

# Actual vs Predicted plot (sample 2000 points)
n_plot = min(2000, len(y_teA))
step = max(1, len(y_teA) // n_plot)
fig, ax = plt.subplots(figsize=(16, 5))
idx = range(0, len(y_teA), step)
ax.plot([i for i in idx], y_teA.values[list(idx)], color='#58a6ff', linewidth=1, label='Actual', alpha=0.85)
ax.plot([i for i in idx], xgb_preds_A[list(idx)], color='#f78166', linewidth=1, label='XGBoost Predicted', alpha=0.85)
ax.set_title(f'Exp A — Minute-level: Actual vs Predicted  (RMSE={xgb_met_A["RMSE"]:.4f}, R²={xgb_met_A["R2"]:.4f})',
             color='#c9d1d9', fontsize=12)
ax.set_xlabel('Time Steps (minutes)')
ax.set_ylabel('% Silica Concentrate')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'p5_expA_actual_vs_pred.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: p5_expA_actual_vs_pred.png")

# ══════════════════════════════════════════════════════════════
# EXPERIMENT B: Multi-step ahead prediction (Q2)
# ══════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("EXPERIMENT B — Multi-step Ahead Prediction (Q2)")
print("─" * 60)

df_multi = pd.read_parquet(os.path.join(RESULTS_DIR, 'features_multistep.parquet'))
horizons = [1, 2, 4, 8, 12]
horizon_metrics = {}

base_feats = [c for c in df_multi.columns
              if c not in [TARGET, IRON_COL] and not c.startswith('target_') or c.startswith('target_lag')]
# Keep only lag features + process features
base_feats = [c for c in df_multi.columns
              if c not in [TARGET, IRON_COL]
              and not any(c == f'target_{h}h_ahead' for h in horizons)]

for h in horizons:
    target_col = f'target_{h}h_ahead'
    df_h = df_multi[base_feats + [target_col]].dropna()
    train_h, test_h = time_split(df_h)
    X_tr, y_tr = train_h[base_feats], train_h[target_col]
    X_te, y_te = test_h[base_feats],  test_h[target_col]

    model_h, preds_h, met_h = train_xgb(X_tr, y_tr, X_te, y_te)
    print(f"  {h:>2}h ahead — RMSE:{met_h['RMSE']:.4f}  MAE:{met_h['MAE']:.4f}  R²:{met_h['R2']:.4f}")
    horizon_metrics[h] = met_h
    joblib.dump(model_h, os.path.join(MODELS_DIR, f'xgb_horizon_{h}h.pkl'))

all_results['experiment_B'] = {
    'description': 'Multi-step ahead prediction — RMSE by forecast horizon',
    'horizon_metrics': horizon_metrics
}

# Plot RMSE degradation
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle('Exp B — Forecast Horizon Analysis (How far ahead can we predict?)',
             fontsize=13, color='#c9d1d9')

rmse_vals = [horizon_metrics[h]['RMSE'] for h in horizons]
r2_vals   = [horizon_metrics[h]['R2']   for h in horizons]
mae_vals  = [horizon_metrics[h]['MAE']  for h in horizons]

axes[0].plot(horizons, rmse_vals, 'o-', color='#f78166', linewidth=2.5, markersize=8)
axes[0].fill_between(horizons, rmse_vals, alpha=0.15, color='#f78166')
axes[0].set_title('RMSE vs Forecast Horizon', color='#c9d1d9')
axes[0].set_xlabel('Hours Ahead'); axes[0].set_ylabel('RMSE')
axes[0].grid(True, alpha=0.3); axes[0].set_xticks(horizons)

axes[1].plot(horizons, r2_vals, 'o-', color='#3fb950', linewidth=2.5, markersize=8)
axes[1].fill_between(horizons, r2_vals, alpha=0.15, color='#3fb950')
axes[1].axhline(y=0.8, color='white', linestyle='--', alpha=0.5, label='R²=0.8 threshold')
axes[1].set_title('R² vs Forecast Horizon', color='#c9d1d9')
axes[1].set_xlabel('Hours Ahead'); axes[1].set_ylabel('R²')
axes[1].legend(); axes[1].grid(True, alpha=0.3); axes[1].set_xticks(horizons)

axes[2].plot(horizons, mae_vals, 'o-', color='#bc8cff', linewidth=2.5, markersize=8)
axes[2].fill_between(horizons, mae_vals, alpha=0.15, color='#bc8cff')
axes[2].set_title('MAE vs Forecast Horizon', color='#c9d1d9')
axes[2].set_xlabel('Hours Ahead'); axes[2].set_ylabel('MAE')
axes[2].grid(True, alpha=0.3); axes[2].set_xticks(horizons)

plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'p6_expB_horizon_analysis.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: p6_expB_horizon_analysis.png")

# ══════════════════════════════════════════════════════════════
# EXPERIMENT C: Without Iron Concentrate (Q3)
# ══════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("EXPERIMENT C — Without % Iron Concentrate (Q3)")
print("─" * 60)

df_min = pd.read_parquet(os.path.join(RESULTS_DIR, 'features_1min.parquet'))

# WITH iron (already done in A)
feats_with = [c for c in df_min.columns if c not in [TARGET, IRON_COL]]
# WITHOUT iron — remove any cols that might encode iron
feats_without = [c for c in feats_with if 'Iron' not in c and 'iron' not in c]

train_C, test_C = time_split(df_min)

# Model WITH iron
xgb_with, preds_with, met_with = train_xgb(
    train_C[feats_with], train_C[TARGET],
    test_C[feats_with],  test_C[TARGET]
)

# Model WITHOUT iron
xgb_without, preds_without, met_without = train_xgb(
    train_C[feats_without], train_C[TARGET],
    test_C[feats_without],  test_C[TARGET]
)

print(f"  WITH Iron     — RMSE:{met_with['RMSE']:.4f}  MAE:{met_with['MAE']:.4f}  R²:{met_with['R2']:.4f}")
print(f"  WITHOUT Iron  — RMSE:{met_without['RMSE']:.4f}  MAE:{met_without['MAE']:.4f}  R²:{met_without['R2']:.4f}")

rmse_diff = round(met_without['RMSE'] - met_with['RMSE'], 4)
r2_diff   = round(met_with['R2']   - met_without['R2'],   4)
print(f"\n  RMSE increase without Iron: +{rmse_diff:.4f}")
print(f"  R²   decrease without Iron: -{r2_diff:.4f}")

all_results['experiment_C'] = {
    'description': 'Prediction with vs without % Iron Concentrate column',
    'with_iron':    met_with,
    'without_iron': met_without,
    'rmse_diff':    rmse_diff,
    'r2_diff':      r2_diff,
    'verdict': 'feasible' if met_without['R2'] > 0.75 else 'degraded'
}

joblib.dump(xgb_without, os.path.join(MODELS_DIR, 'xgb_expC_no_iron.pkl'))
np.save(os.path.join(RESULTS_DIR, 'preds_expC_with.npy'), preds_with)
np.save(os.path.join(RESULTS_DIR, 'preds_expC_without.npy'), preds_without)

# Comparison bar chart
fig, axes = plt.subplots(1, 3, figsize=(14, 5))
fig.suptitle('Exp C — With vs Without % Iron Concentrate Feature', fontsize=13, color='#c9d1d9')
metrics = ['RMSE', 'MAE', 'R2']
labels  = ['With Iron', 'Without Iron']
bar_colors = ['#58a6ff', '#f78166']
for ax, metric in zip(axes, metrics):
    vals = [met_with[metric], met_without[metric]]
    bars = ax.bar(labels, vals, color=bar_colors, edgecolor='none', width=0.5)
    ax.set_title(metric, color='#c9d1d9')
    ax.set_ylabel(metric)
    ax.grid(True, alpha=0.3, axis='y')
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
                f'{v:.4f}', ha='center', va='bottom', fontsize=10, color='#c9d1d9')
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'p7_expC_iron_comparison.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: p7_expC_iron_comparison.png")

# ── Feature Importance Plot ────────────────────────────────────────────────────
print("\n[Extra] Feature importance plot...")
fi_A = pd.Series(xgb_A.feature_importances_, index=feats_A).sort_values(ascending=False).head(20)
fig, ax = plt.subplots(figsize=(10, 8))
bars = ax.barh(fi_A.index[::-1], fi_A.values[::-1], color='#58a6ff', edgecolor='none')
ax.set_title('Top 20 Feature Importances (XGBoost — Exp A)', color='#c9d1d9', fontsize=13)
ax.set_xlabel('Importance Score')
ax.grid(True, alpha=0.3, axis='x')
# Color target lag features differently
for i, (label, bar) in enumerate(zip(fi_A.index[::-1], bars)):
    if 'target_lag' in label:
        bar.set_color('#f78166')
    elif 'roll' in label:
        bar.set_color('#3fb950')
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'p8_feature_importance.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  Saved: p8_feature_importance.png")

# ── Save all results ───────────────────────────────────────────────────────────
with open(os.path.join(RESULTS_DIR, 'model_results.json'), 'w') as f:
    json.dump(all_results, f, indent=2)

print("\n✅ Model training complete!")
print(f"   All results → outputs/results/model_results.json")
print(f"   All models  → outputs/models/")
print(f"   All plots   → outputs/plots/")
