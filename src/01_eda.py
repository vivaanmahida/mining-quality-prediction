"""
01_eda.py - Exploratory Data Analysis
Mining Process Quality Prediction Project
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import warnings
import os

warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH  = os.path.join(BASE_DIR, "data", "MiningProcess_Flotation_Plant_Database.csv")
PLOTS_DIR  = os.path.join(BASE_DIR, "outputs", "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# ── Style ──────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    'figure.facecolor': '#0d1117',
    'axes.facecolor':   '#161b22',
    'axes.edgecolor':   '#30363d',
    'axes.labelcolor':  '#c9d1d9',
    'text.color':       '#c9d1d9',
    'xtick.color':      '#8b949e',
    'ytick.color':      '#8b949e',
    'grid.color':       '#21262d',
    'grid.alpha':       0.6,
    'font.family':      'DejaVu Sans',
    'axes.titlesize':   13,
    'axes.labelsize':   11,
    'legend.facecolor': '#161b22',
    'legend.edgecolor': '#30363d',
    'legend.labelcolor':'#c9d1d9',
})
ACCENT = '#58a6ff'
ORANGE = '#f78166'
GREEN  = '#3fb950'
PURPLE = '#bc8cff'

print("=" * 60)
print("  MINING QUALITY PREDICTION — EDA")
print("=" * 60)

# ── Load Data ──────────────────────────────────────────────────────────────────
print("\n[1/6] Loading dataset...")
df = pd.read_csv(DATA_PATH, sep=',', decimal=',')

# Fix datetime
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d %H:%M:%S')
df = df.sort_values('date').reset_index(drop=True)
df = df.set_index('date')

# Strip column names
df.columns = [c.strip() for c in df.columns]

print(f"      Shape       : {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"      Date range  : {df.index[0]}  →  {df.index[-1]}")
print(f"      Duration    : {(df.index[-1] - df.index[0]).days} days")
print(f"      Sample freq : {df.index.to_series().diff().mode()[0]}")

# ── Basic Stats ────────────────────────────────────────────────────────────────
print("\n[2/6] Descriptive statistics for target...")
target = '% Silica Concentrate'
iron   = '% Iron Concentrate'
print(df[[iron, target]].describe().round(4).to_string())

# Missing values
miss = df.isnull().sum()
print(f"\n      Missing values: {miss.sum()} total")

# ── Plot 1: Target Time Series ─────────────────────────────────────────────────
print("\n[3/6] Plotting target time series...")
fig, axes = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
fig.suptitle('% Silica Concentrate — Time Series Overview', fontsize=15, color='#c9d1d9', y=1.01)

# Raw (every 20s — too dense, sample for viz)
sample = df[target].resample('1h').mean()
axes[0].plot(sample.index, sample.values, color=ORANGE, linewidth=1.2, alpha=0.9)
axes[0].set_ylabel('% Silica Concentrate')
axes[0].set_title('Hourly Average (March – September 2017)', color='#c9d1d9')
axes[0].grid(True, alpha=0.3)
axes[0].fill_between(sample.index, sample.values, alpha=0.15, color=ORANGE)

# Iron
iron_sample = df[iron].resample('1h').mean()
axes[1].plot(iron_sample.index, iron_sample.values, color=ACCENT, linewidth=1.2, alpha=0.9)
axes[1].set_ylabel('% Iron Concentrate')
axes[1].set_title('% Iron Concentrate — Hourly Average', color='#c9d1d9')
axes[1].grid(True, alpha=0.3)
axes[1].fill_between(iron_sample.index, iron_sample.values, alpha=0.15, color=ACCENT)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))

plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'p1_target_timeseries.png'), dpi=150, bbox_inches='tight')
plt.close()
print("      Saved: p1_target_timeseries.png")

# ── Plot 2: Distribution ───────────────────────────────────────────────────────
print("\n[4/6] Plotting distributions...")
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle('Distribution of Key Variables', fontsize=14, color='#c9d1d9')

cols_dist = [
    ('% Iron Feed',       GREEN),
    ('% Silica Feed',     PURPLE),
    ('% Silica Concentrate', ORANGE),
]
for ax, (col, color) in zip(axes, cols_dist):
    vals = df[col].dropna()
    ax.hist(vals, bins=60, color=color, alpha=0.8, edgecolor='none')
    ax.axvline(vals.mean(), color='white', linestyle='--', linewidth=1.5, label=f'Mean: {vals.mean():.2f}')
    ax.axvline(vals.median(), color='yellow', linestyle=':', linewidth=1.5, label=f'Median: {vals.median():.2f}')
    ax.set_title(col, color='#c9d1d9')
    ax.set_xlabel('Value')
    ax.set_ylabel('Frequency')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'p2_distributions.png'), dpi=150, bbox_inches='tight')
plt.close()
print("      Saved: p2_distributions.png")

# ── Plot 3: Correlation Heatmap ────────────────────────────────────────────────
print("\n[5/6] Plotting correlation heatmap...")

# Resample to hourly to align all columns
df_hourly = df.resample('1h').mean()
corr = df_hourly.corr()

fig, ax = plt.subplots(figsize=(14, 11))
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

mask = np.zeros_like(corr, dtype=bool)
mask[np.triu_indices_from(mask)] = True

cmap = sns.diverging_palette(220, 20, as_cmap=True)
sns.heatmap(
    corr, mask=mask, cmap=cmap, vmax=1, vmin=-1, center=0,
    square=True, linewidths=0.3, linecolor='#0d1117',
    annot=True, fmt='.2f', annot_kws={'size': 7, 'color': '#c9d1d9'},
    ax=ax, cbar_kws={'shrink': 0.8}
)
ax.set_title('Feature Correlation Matrix (Hourly Resampled)', color='#c9d1d9', fontsize=14, pad=15)
ax.tick_params(colors='#8b949e', labelsize=8)

plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'p3_correlation_heatmap.png'), dpi=150, bbox_inches='tight')
plt.close()
print("      Saved: p3_correlation_heatmap.png")

# ── Plot 4: Silica vs Iron Scatter ─────────────────────────────────────────────
print("\n[6/6] Plotting Iron vs Silica relationship...")
fig, ax = plt.subplots(figsize=(9, 7))
sc = ax.scatter(df_hourly[iron], df_hourly[target],
                alpha=0.35, s=12, c=df_hourly[target],
                cmap='plasma', edgecolors='none')
plt.colorbar(sc, ax=ax, label='% Silica Concentrate')
m, b = np.polyfit(df_hourly[iron].dropna(), df_hourly[target].dropna(), 1)
x_line = np.linspace(df_hourly[iron].min(), df_hourly[iron].max(), 200)
ax.plot(x_line, m*x_line+b, color=ORANGE, linewidth=2, linestyle='--', label=f'Linear fit  (slope={m:.2f})')
corr_val = df_hourly[[iron, target]].corr().iloc[0,1]
ax.set_title(f'% Iron vs % Silica Concentrate\n(Pearson r = {corr_val:.4f})', color='#c9d1d9', fontsize=13)
ax.set_xlabel('% Iron Concentrate')
ax.set_ylabel('% Silica Concentrate')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'p4_iron_vs_silica.png'), dpi=150, bbox_inches='tight')
plt.close()
print("      Saved: p4_iron_vs_silica.png")

# ── Save correlation with target ───────────────────────────────────────────────
target_corr = corr[target].drop(target).sort_values(key=abs, ascending=False)
print("\n📊 Top correlations with % Silica Concentrate:")
print(target_corr.head(10).to_string())

import json
results = {
    'shape': list(df.shape),
    'date_start': str(df.index[0]),
    'date_end':   str(df.index[-1]),
    'n_days': int((df.index[-1] - df.index[0]).days),
    'target_mean':  round(float(df[target].mean()), 4),
    'target_std':   round(float(df[target].std()),  4),
    'target_min':   round(float(df[target].min()),  4),
    'target_max':   round(float(df[target].max()),  4),
    'iron_silica_corr': round(float(corr_val), 4),
    'top_correlations': {k: round(float(v), 4) for k, v in target_corr.head(10).items()}
}
results_path = os.path.join(BASE_DIR, "outputs", "results", "eda_stats.json")
with open(results_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✅ EDA complete. Stats saved to outputs/results/eda_stats.json")
print(f"   All plots saved to outputs/plots/")
