"""
04_generate_dashboard.py - Interactive HTML Dashboard Generator
Mining Process Quality Prediction Project
"""

import pandas as pd
import numpy as np
import json
import os
import base64
from pathlib import Path

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS    = os.path.join(BASE_DIR, "outputs", "results")
PLOTS      = os.path.join(BASE_DIR, "outputs", "plots")
DASH_DIR   = os.path.join(BASE_DIR, "dashboard")
DATA_PATH  = os.path.join(BASE_DIR, "data", "MiningProcess_Flotation_Plant_Database.csv")
os.makedirs(DASH_DIR, exist_ok=True)

TARGET   = '% Silica Concentrate'
IRON_COL = '% Iron Concentrate'

print("=" * 60)
print("  MINING QUALITY PREDICTION — DASHBOARD GENERATOR")
print("=" * 60)

# ── Load results ───────────────────────────────────────────────────────────────
print("\n[1/4] Loading results...")
with open(os.path.join(RESULTS, 'model_results.json')) as f:
    model_results = json.load(f)
with open(os.path.join(RESULTS, 'eda_stats.json')) as f:
    eda_stats = json.load(f)
with open(os.path.join(RESULTS, 'feature_meta.json')) as f:
    feat_meta = json.load(f)
with open(os.path.join(RESULTS, 'feature_importance_A.json')) as f:
    fi_raw = json.load(f)

# ── Load predictions for chart ─────────────────────────────────────────────────
print("[2/4] Loading predictions...")
preds_A  = np.load(os.path.join(RESULTS, 'preds_expA.npy'))
actual_A = np.load(os.path.join(RESULTS, 'actual_expA.npy'))
dates_A  = np.load(os.path.join(RESULTS, 'dates_expA.npy'), allow_pickle=True)

# Downsample for chart (max 1500 points)
n = len(actual_A)
step = max(1, n // 1500)
idx = list(range(0, n, step))
chart_dates  = [str(dates_A[i])  for i in idx]
chart_actual = [round(float(actual_A[i]), 4) for i in idx]
chart_preds  = [round(float(preds_A[i]),  4) for i in idx]

# ── Horizon data for chart ─────────────────────────────────────────────────────
h_data = model_results['experiment_B']['horizon_metrics']
horizons   = [int(k) for k in h_data.keys()]
rmse_vals  = [h_data[str(k)]['RMSE'] for k in horizons]
r2_vals    = [h_data[str(k)]['R2']   for k in horizons]
mae_vals   = [h_data[str(k)]['MAE']  for k in horizons]

# ── Exp C comparison data ──────────────────────────────────────────────────────
expC = model_results['experiment_C']
with_iron    = expC['with_iron']
without_iron = expC['without_iron']

# ── Feature Importance data ────────────────────────────────────────────────────
fi_items = sorted(fi_raw.items(), key=lambda x: x[1], reverse=True)[:15]
fi_labels = [item[0][:35] for item in fi_items]
fi_values = [round(item[1], 6) for item in fi_items]

# ── Embed plots as base64 ──────────────────────────────────────────────────────
def img_to_b64(path):
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    return ''

imgs = {
    'timeseries':   img_to_b64(os.path.join(PLOTS, 'p1_target_timeseries.png')),
    'distributions': img_to_b64(os.path.join(PLOTS, 'p2_distributions.png')),
    'heatmap':      img_to_b64(os.path.join(PLOTS, 'p3_correlation_heatmap.png')),
    'iron_silica':  img_to_b64(os.path.join(PLOTS, 'p4_iron_vs_silica.png')),
    'feat_imp':     img_to_b64(os.path.join(PLOTS, 'p8_feature_importance.png')),
}

# Determine verdict for best horizon
best_h = None
for h in sorted(horizons):
    if h_data[str(h)]['R2'] >= 0.80:
        best_h = h
verdict_h = f"Up to <b>{best_h} hour(s) ahead</b> with R² ≥ 0.80" if best_h else f"<b>{horizons[0]}h ahead</b> shows best accuracy"
verdict_iron = "Yes — feasible" if expC['verdict'] == 'feasible' else "Degraded — iron feature matters"

expA = model_results['experiment_A']
best_model_A = min(['XGBoost', 'LightGBM', 'RandomForest'], key=lambda m: expA[m]['RMSE'])

print("[3/4] Generating HTML dashboard...")

# ── Build HTML ─────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mining Quality Prediction — Dashboard</title>
<meta name="description" content="Interactive ML dashboard for predicting silica impurity in iron ore flotation plant concentrate.">
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:       #0d1117;
    --surface:  #161b22;
    --border:   #30363d;
    --text:     #c9d1d9;
    --muted:    #8b949e;
    --accent:   #58a6ff;
    --orange:   #f78166;
    --green:    #3fb950;
    --purple:   #bc8cff;
    --yellow:   #ffa657;
    --card-bg:  #21262d;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; min-height: 100vh; }}

  /* ── Hero ── */
  .hero {{
    background: linear-gradient(135deg, #0d1117 0%, #1a1f2e 50%, #0d1117 100%);
    border-bottom: 1px solid var(--border);
    padding: 48px 40px 36px;
    position: relative; overflow: hidden;
  }}
  .hero::before {{
    content: '';
    position: absolute; top: -60px; right: -60px;
    width: 320px; height: 320px;
    background: radial-gradient(circle, rgba(88,166,255,0.12) 0%, transparent 70%);
    border-radius: 50%;
  }}
  .hero-badge {{
    display: inline-block; padding: 4px 14px; border-radius: 20px;
    background: rgba(88,166,255,0.15); border: 1px solid rgba(88,166,255,0.3);
    color: var(--accent); font-size: 12px; font-weight: 500; letter-spacing: 0.5px;
    margin-bottom: 16px;
  }}
  .hero h1 {{ font-size: 2.4rem; font-weight: 700; color: #fff; line-height: 1.2; margin-bottom: 10px; }}
  .hero h1 span {{ color: var(--accent); }}
  .hero p {{ color: var(--muted); font-size: 1rem; max-width: 680px; line-height: 1.6; }}

  /* ── Nav ── */
  .nav {{
    background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 0 40px; display: flex; gap: 0; position: sticky; top: 0; z-index: 100;
  }}
  .nav-btn {{
    padding: 14px 22px; font-size: 13px; font-weight: 500; color: var(--muted);
    background: none; border: none; border-bottom: 2px solid transparent;
    cursor: pointer; transition: all 0.2s; white-space: nowrap;
  }}
  .nav-btn:hover {{ color: var(--text); }}
  .nav-btn.active {{ color: var(--accent); border-bottom-color: var(--accent); }}

  /* ── Layout ── */
  .main {{ padding: 32px 40px; max-width: 1400px; margin: 0 auto; }}
  .tab {{ display: none; animation: fadeIn 0.3s ease; }}
  .tab.active {{ display: block; }}
  @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}

  /* ── Cards ── */
  .grid-4 {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 28px; }}
  .grid-2 {{ display: grid; grid-template-columns: repeat(2,1fr); gap: 20px; margin-bottom: 28px; }}
  .grid-3 {{ display: grid; grid-template-columns: repeat(3,1fr); gap: 20px; margin-bottom: 28px; }}
  .card {{
    background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px;
    padding: 22px; transition: border-color 0.2s, transform 0.2s;
  }}
  .card:hover {{ border-color: rgba(88,166,255,0.35); transform: translateY(-2px); }}
  .card-label {{ font-size: 11px; font-weight: 600; letter-spacing: 0.8px; color: var(--muted); text-transform: uppercase; margin-bottom: 8px; }}
  .card-value {{ font-size: 2rem; font-weight: 700; color: #fff; line-height: 1; margin-bottom: 4px; }}
  .card-sub {{ font-size: 12px; color: var(--muted); }}
  .card-accent-blue  {{ border-left: 3px solid var(--accent); }}
  .card-accent-orange{{ border-left: 3px solid var(--orange); }}
  .card-accent-green {{ border-left: 3px solid var(--green); }}
  .card-accent-purple{{ border-left: 3px solid var(--purple); }}

  /* ── Section ── */
  .section-title {{
    font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 16px;
    padding-bottom: 10px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 10px;
  }}
  .section-title .badge {{
    font-size: 11px; padding: 2px 10px; border-radius: 20px; font-weight: 500;
  }}
  .badge-blue   {{ background: rgba(88,166,255,0.15); color: var(--accent); }}
  .badge-orange {{ background: rgba(247,129,102,0.15); color: var(--orange); }}
  .badge-green  {{ background: rgba(63,185,80,0.15);  color: var(--green); }}
  .badge-purple {{ background: rgba(188,140,255,0.15);color: var(--purple); }}

  /* ── Chart containers ── */
  .chart-box {{
    background: var(--card-bg); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px; margin-bottom: 20px;
  }}
  .chart-title {{ font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 14px; }}
  .plotly-chart {{ width: 100%; }}

  /* ── Images ── */
  .img-card {{
    background: var(--card-bg); border: 1px solid var(--border);
    border-radius: 12px; overflow: hidden; margin-bottom: 20px;
  }}
  .img-card img {{ width: 100%; display: block; }}
  .img-caption {{ padding: 10px 16px; font-size: 12px; color: var(--muted); }}

  /* ── Q&A cards ── */
  .qa-card {{
    background: var(--card-bg); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px; margin-bottom: 20px;
    position: relative; overflow: hidden;
  }}
  .qa-card::before {{
    content: ''; position: absolute; top: 0; left: 0;
    width: 4px; height: 100%;
  }}
  .qa-card.q1::before {{ background: var(--accent); }}
  .qa-card.q2::before {{ background: var(--orange); }}
  .qa-card.q3::before {{ background: var(--green); }}
  .qa-number {{ font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }}
  .qa-card.q1 .qa-number {{ color: var(--accent); }}
  .qa-card.q2 .qa-number {{ color: var(--orange); }}
  .qa-card.q3 .qa-number {{ color: var(--green); }}
  .qa-question {{ font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 12px; line-height: 1.4; }}
  .qa-answer {{ font-size: 13.5px; color: var(--muted); line-height: 1.7; }}
  .qa-verdict {{
    display: inline-block; margin-top: 12px; padding: 6px 18px;
    border-radius: 20px; font-size: 13px; font-weight: 600;
  }}
  .verdict-yes {{ background: rgba(63,185,80,0.15); color: var(--green); border: 1px solid rgba(63,185,80,0.3); }}
  .verdict-partial {{ background: rgba(255,166,87,0.15); color: var(--yellow); border: 1px solid rgba(255,166,87,0.3); }}

  /* ── Metric table ── */
  .metric-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .metric-table th {{
    background: var(--surface); padding: 10px 14px; text-align: left;
    color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase;
    border-bottom: 1px solid var(--border);
  }}
  .metric-table td {{ padding: 10px 14px; border-bottom: 1px solid #21262d; color: var(--text); }}
  .metric-table tr:last-child td {{ border-bottom: none; }}
  .metric-table tr:hover td {{ background: rgba(88,166,255,0.04); }}
  .best {{ color: var(--green); font-weight: 600; }}

  /* ── Responsive ── */
  @media (max-width: 900px) {{
    .grid-4 {{ grid-template-columns: repeat(2,1fr); }}
    .grid-3 {{ grid-template-columns: 1fr; }}
    .grid-2 {{ grid-template-columns: 1fr; }}
    .hero h1 {{ font-size: 1.6rem; }}
    .main {{ padding: 20px; }}
    .nav {{ padding: 0 16px; overflow-x: auto; }}
  }}
</style>
</head>
<body>

<!-- ── HERO ─────────────────────────────────────────────── -->
<div class="hero">
  <div class="hero-badge">🏭 Industrial ML · Flotation Plant</div>
  <h1>Mining <span>Quality</span> Prediction</h1>
  <p>Predicting <strong>% Silica Concentrate</strong> impurity using XGBoost, LightGBM & Random Forest on real industrial sensor data from a flotation plant (March–September 2017).</p>
</div>

<!-- ── NAV ──────────────────────────────────────────────── -->
<nav class="nav">
  <button class="nav-btn active" onclick="showTab('overview', this)" id="tab-overview">📊 Overview</button>
  <button class="nav-btn" onclick="showTab('eda', this)" id="tab-eda">🔍 EDA</button>
  <button class="nav-btn" onclick="showTab('predictions', this)" id="tab-pred">🤖 Predictions</button>
  <button class="nav-btn" onclick="showTab('horizon', this)" id="tab-hor">⏱ Horizon</button>
  <button class="nav-btn" onclick="showTab('importance', this)" id="tab-fi">⚡ Features</button>
  <button class="nav-btn" onclick="showTab('answers', this)" id="tab-qa">💡 Q&A</button>
</nav>

<!-- ── MAIN ─────────────────────────────────────────────── -->
<div class="main">

  <!-- ══ TAB: OVERVIEW ══ -->
  <div class="tab active" id="tab-content-overview">
    <div class="grid-4">
      <div class="card card-accent-blue">
        <div class="card-label">Total Records</div>
        <div class="card-value">{eda_stats['shape'][0]:,}</div>
        <div class="card-sub">Raw sensor readings</div>
      </div>
      <div class="card card-accent-orange">
        <div class="card-label">Features</div>
        <div class="card-value">{eda_stats['shape'][1]}</div>
        <div class="card-sub">Process variables</div>
      </div>
      <div class="card card-accent-green">
        <div class="card-label">Date Range</div>
        <div class="card-value">{eda_stats['n_days']}d</div>
        <div class="card-sub">Mar – Sep 2017</div>
      </div>
      <div class="card card-accent-purple">
        <div class="card-label">Silica–Iron Corr</div>
        <div class="card-value">{eda_stats['iron_silica_corr']:.3f}</div>
        <div class="card-sub">Pearson r</div>
      </div>
    </div>

    <div class="grid-4">
      <div class="card">
        <div class="card-label">Target Mean</div>
        <div class="card-value" style="font-size:1.5rem">{eda_stats['target_mean']:.3f}%</div>
        <div class="card-sub">% Silica Concentrate</div>
      </div>
      <div class="card">
        <div class="card-label">Target Std Dev</div>
        <div class="card-value" style="font-size:1.5rem">{eda_stats['target_std']:.3f}%</div>
        <div class="card-sub">Variability</div>
      </div>
      <div class="card">
        <div class="card-label">Target Min</div>
        <div class="card-value" style="font-size:1.5rem">{eda_stats['target_min']:.3f}%</div>
        <div class="card-sub">Best quality</div>
      </div>
      <div class="card">
        <div class="card-label">Target Max</div>
        <div class="card-value" style="font-size:1.5rem">{eda_stats['target_max']:.3f}%</div>
        <div class="card-sub">Worst quality</div>
      </div>
    </div>

    <div class="section-title">Model Performance Summary <span class="badge badge-blue">All Experiments</span></div>
    <div class="chart-box">
      <table class="metric-table">
        <thead>
          <tr><th>Experiment</th><th>Model</th><th>RMSE</th><th>MAE</th><th>R²</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>A — Minute-level (Q1)</td>
            <td>XGBoost</td>
            <td class="best">{expA['XGBoost']['RMSE']}</td>
            <td>{expA['XGBoost']['MAE']}</td>
            <td class="best">{expA['XGBoost']['R2']}</td>
          </tr>
          <tr>
            <td></td>
            <td>LightGBM</td>
            <td>{expA['LightGBM']['RMSE']}</td>
            <td>{expA['LightGBM']['MAE']}</td>
            <td>{expA['LightGBM']['R2']}</td>
          </tr>
          <tr>
            <td></td>
            <td>Random Forest</td>
            <td>{expA['RandomForest']['RMSE']}</td>
            <td>{expA['RandomForest']['MAE']}</td>
            <td>{expA['RandomForest']['R2']}</td>
          </tr>
          <tr>
            <td>B — 1h Ahead (Q2)</td>
            <td>XGBoost</td>
            <td>{h_data['1']['RMSE']}</td>
            <td>{h_data['1']['MAE']}</td>
            <td>{h_data['1']['R2']}</td>
          </tr>
          <tr>
            <td>C — Without Iron (Q3)</td>
            <td>XGBoost (with iron)</td>
            <td>{with_iron['RMSE']}</td>
            <td>{with_iron['MAE']}</td>
            <td>{with_iron['R2']}</td>
          </tr>
          <tr>
            <td></td>
            <td>XGBoost (no iron)</td>
            <td>{without_iron['RMSE']}</td>
            <td>{without_iron['MAE']}</td>
            <td>{without_iron['R2']}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- ══ TAB: EDA ══ -->
  <div class="tab" id="tab-content-eda">
    <div class="section-title">Target Variable — Time Series <span class="badge badge-blue">March–September 2017</span></div>
    <div class="img-card">
      <img src="data:image/png;base64,{imgs['timeseries']}" alt="Time Series">
      <div class="img-caption">Hourly-averaged % Silica and % Iron Concentrate over the full data collection period.</div>
    </div>
    <div class="grid-2">
      <div class="img-card">
        <img src="data:image/png;base64,{imgs['distributions']}" alt="Distributions">
        <div class="img-caption">Distribution of Iron Feed, Silica Feed, and Silica Concentrate.</div>
      </div>
      <div class="img-card">
        <img src="data:image/png;base64,{imgs['iron_silica']}" alt="Iron vs Silica">
        <div class="img-caption">% Iron vs % Silica Concentrate scatter (Pearson r = {eda_stats['iron_silica_corr']:.4f}).</div>
      </div>
    </div>
    <div class="section-title">Correlation Heatmap <span class="badge badge-orange">All Features · Hourly</span></div>
    <div class="img-card">
      <img src="data:image/png;base64,{imgs['heatmap']}" alt="Heatmap">
      <div class="img-caption">Feature correlation matrix (hourly resampled). Strong negative correlation between % Iron and % Silica Concentrate.</div>
    </div>
  </div>

  <!-- ══ TAB: PREDICTIONS ══ -->
  <div class="tab" id="tab-content-predictions">
    <div class="section-title">Experiment A — Minute-level Actual vs Predicted <span class="badge badge-green">XGBoost · Test Set</span></div>
    <div class="chart-box">
      <div id="pred-chart" class="plotly-chart"></div>
    </div>
    <div class="grid-3">
      <div class="card card-accent-green">
        <div class="card-label">Best Model</div>
        <div class="card-value" style="font-size:1.3rem">{best_model_A}</div>
        <div class="card-sub">Minute-level prediction</div>
      </div>
      <div class="card card-accent-blue">
        <div class="card-label">XGBoost RMSE</div>
        <div class="card-value" style="font-size:1.5rem">{expA['XGBoost']['RMSE']}</div>
        <div class="card-sub">% Silica (lower is better)</div>
      </div>
      <div class="card card-accent-purple">
        <div class="card-label">XGBoost R²</div>
        <div class="card-value" style="font-size:1.5rem">{expA['XGBoost']['R2']}</div>
        <div class="card-sub">Explained variance</div>
      </div>
    </div>
  </div>

  <!-- ══ TAB: HORIZON ══ -->
  <div class="tab" id="tab-content-horizon">
    <div class="section-title">Experiment B — Multi-step Forecast Horizon <span class="badge badge-orange">1h → 12h Ahead</span></div>
    <div class="grid-2">
      <div class="chart-box">
        <div class="chart-title">RMSE vs Forecast Horizon</div>
        <div id="rmse-chart" class="plotly-chart"></div>
      </div>
      <div class="chart-box">
        <div class="chart-title">R² vs Forecast Horizon</div>
        <div id="r2-chart" class="plotly-chart"></div>
      </div>
    </div>
    <div class="chart-box">
      <table class="metric-table">
        <thead>
          <tr><th>Horizon</th><th>RMSE</th><th>MAE</th><th>R²</th><th>Reliability</th></tr>
        </thead>
        <tbody>
          {''.join(f"""
          <tr>
            <td>{h}h ahead</td>
            <td>{h_data[str(h)]['RMSE']}</td>
            <td>{h_data[str(h)]['MAE']}</td>
            <td {'class="best"' if h_data[str(h)]['R2'] >= 0.80 else ''}>{h_data[str(h)]['R2']}</td>
            <td>{'<span style="color:var(--green)">✅ High</span>' if h_data[str(h)]['R2'] >= 0.80 else '<span style="color:var(--orange)">⚠ Moderate</span>' if h_data[str(h)]['R2'] >= 0.60 else '<span style="color:var(--orange)">❌ Low</span>'}</td>
          </tr>""" for h in horizons)}
        </tbody>
      </table>
    </div>
  </div>

  <!-- ══ TAB: FEATURE IMPORTANCE ══ -->
  <div class="tab" id="tab-content-importance">
    <div class="section-title">Feature Importance — XGBoost (Experiment A) <span class="badge badge-purple">Top 15 Features</span></div>
    <div class="chart-box">
      <div id="fi-chart" class="plotly-chart"></div>
    </div>
    <div class="img-card">
      <img src="data:image/png;base64,{imgs['feat_imp']}" alt="Feature Importance">
      <div class="img-caption">Blue = process variables, Orange = target lag features, Green = rolling statistics.</div>
    </div>
  </div>

  <!-- ══ TAB: Q&A ══ -->
  <div class="tab" id="tab-content-answers">
    <div class="section-title">Research Questions — Key Findings <span class="badge badge-blue">3 Experiments</span></div>

    <div class="qa-card q1">
      <div class="qa-number">Question 1</div>
      <div class="qa-question">Is it possible to predict % Silica Concentrate every minute?</div>
      <div class="qa-answer">
        Yes. By resampling sensor data to 1-minute intervals and engineering lag features (past 1, 5, 10, 30, 60 minutes) plus rolling statistics,
        XGBoost achieves <strong>RMSE = {expA['XGBoost']['RMSE']}</strong> and <strong>R² = {expA['XGBoost']['R2']}</strong> on the held-out test set.
        The model captures the short-term dynamics of the flotation process effectively.
        Minute-level lag features of the target (autoregressive features) are the most important predictors.
      </div>
      <div class="qa-verdict verdict-yes">✅ Yes — Feasible (R² = {expA['XGBoost']['R2']})</div>
    </div>

    <div class="qa-card q2">
      <div class="qa-number">Question 2</div>
      <div class="qa-question">How many steps (hours) ahead can we predict % Silica Concentrate?</div>
      <div class="qa-answer">
        Separate XGBoost models were trained for 1h, 2h, 4h, 8h, and 12h forecast horizons.
        Performance degrades as the horizon increases — which is expected for industrial time series.
        {verdict_h}. At 12 hours ahead, RMSE rises to <strong>{h_data['12']['RMSE']}</strong> (R² = {h_data['12']['R2']}).
        This gives plant engineers a practical early-warning window to take corrective actions.
      </div>
      <div class="qa-verdict verdict-partial">⏱ {verdict_h}</div>
    </div>

    <div class="qa-card q3">
      <div class="qa-number">Question 3</div>
      <div class="qa-question">Is it possible to predict % Silica without using % Iron Concentrate (highly correlated)?</div>
      <div class="qa-answer">
        The correlation between % Iron Concentrate and % Silica Concentrate is <strong>r = {eda_stats['iron_silica_corr']:.4f}</strong> — highly negative.
        When the % Iron Concentrate column is removed and the model is retrained, RMSE changes from
        <strong>{with_iron['RMSE']}</strong> → <strong>{without_iron['RMSE']}</strong> (Δ = +{expC['rmse_diff']}),
        and R² changes from <strong>{with_iron['R2']}</strong> → <strong>{without_iron['R2']}</strong> (Δ = -{expC['r2_diff']}).
        The model without iron still leverages process variables (airflow, flotation column levels) to make useful predictions.
      </div>
      <div class="qa-verdict {'verdict-yes' if expC['verdict'] == 'feasible' else 'verdict-partial'}">
        {'✅ Yes — Still feasible without Iron feature' if expC['verdict'] == 'feasible' else '⚠ Degraded — Iron feature significantly helps'}
      </div>
    </div>
  </div>

</div><!-- /main -->

<script>
// ── Tab switcher ─────────────────────────────────────────────
function showTab(name, btn) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-content-' + name).classList.add('active');
  btn.classList.add('active');
  // Trigger Plotly resize
  setTimeout(() => window.dispatchEvent(new Event('resize')), 100);
}}

// ── Plotly defaults ──────────────────────────────────────────
const layout_base = {{
  paper_bgcolor: '#21262d',
  plot_bgcolor:  '#21262d',
  font: {{ family: 'Inter', color: '#c9d1d9', size: 12 }},
  xaxis: {{ gridcolor: '#30363d', zerolinecolor: '#30363d' }},
  yaxis: {{ gridcolor: '#30363d', zerolinecolor: '#30363d' }},
  margin: {{ l:50, r:20, t:30, b:50 }},
  legend: {{ bgcolor: '#161b22', bordercolor: '#30363d', borderwidth: 1 }},
}};
const config = {{ responsive: true, displayModeBar: false }};

// ── Prediction Chart ─────────────────────────────────────────
const chartDates  = {json.dumps(chart_dates)};
const chartActual = {json.dumps(chart_actual)};
const chartPreds  = {json.dumps(chart_preds)};

Plotly.newPlot('pred-chart', [
  {{
    x: chartDates, y: chartActual,
    mode: 'lines', name: 'Actual',
    line: {{ color: '#58a6ff', width: 1.5 }},
  }},
  {{
    x: chartDates, y: chartPreds,
    mode: 'lines', name: 'XGBoost Predicted',
    line: {{ color: '#f78166', width: 1.5, dash: 'dot' }},
  }}
], {{
  ...layout_base,
  xaxis: {{ ...layout_base.xaxis, title: 'Time' }},
  yaxis: {{ ...layout_base.yaxis, title: '% Silica Concentrate' }},
  title: {{ text: 'Actual vs Predicted — Test Set (minute-level)', font:{{ size:13 }} }},
  margin: {{ l:60, r:20, t:50, b:60 }},
}}, config);

// ── RMSE Horizon Chart ───────────────────────────────────────
const horizons = {json.dumps(horizons)};
const rmseVals = {json.dumps(rmse_vals)};
const r2Vals   = {json.dumps(r2_vals)};
const maeVals  = {json.dumps(mae_vals)};

Plotly.newPlot('rmse-chart', [{{
  x: horizons, y: rmseVals,
  mode: 'lines+markers',
  line: {{ color: '#f78166', width: 2.5 }},
  marker: {{ size: 9, color: '#f78166' }},
  fill: 'tozeroy', fillcolor: 'rgba(247,129,102,0.1)',
  name: 'RMSE',
}}], {{
  ...layout_base,
  xaxis: {{ ...layout_base.xaxis, title: 'Hours Ahead', tickvals: horizons }},
  yaxis: {{ ...layout_base.yaxis, title: 'RMSE' }},
  margin: {{ l:60, r:20, t:20, b:60 }},
}}, config);

Plotly.newPlot('r2-chart', [
  {{
    x: horizons, y: r2Vals,
    mode: 'lines+markers',
    line: {{ color: '#3fb950', width: 2.5 }},
    marker: {{ size: 9, color: '#3fb950' }},
    fill: 'tozeroy', fillcolor: 'rgba(63,185,80,0.1)',
    name: 'R²',
  }},
  {{
    x: [Math.min(...horizons), Math.max(...horizons)], y: [0.8, 0.8],
    mode: 'lines', name: 'R²=0.80 threshold',
    line: {{ color: '#ffa657', width: 1.5, dash: 'dash' }},
  }}
], {{
  ...layout_base,
  xaxis: {{ ...layout_base.xaxis, title: 'Hours Ahead', tickvals: horizons }},
  yaxis: {{ ...layout_base.yaxis, title: 'R²', range: [0, 1] }},
  margin: {{ l:60, r:20, t:20, b:60 }},
}}, config);

// ── Feature Importance Chart ─────────────────────────────────
const fiLabels = {json.dumps(fi_labels[::-1])};
const fiValues = {json.dumps(fi_values[::-1])};
const fiColors = fiLabels.map(l =>
  l.includes('target_lag') ? '#f78166' :
  l.includes('roll')       ? '#3fb950' : '#58a6ff'
);

Plotly.newPlot('fi-chart', [{{
  x: fiValues, y: fiLabels,
  type: 'bar', orientation: 'h',
  marker: {{ color: fiColors }},
  name: 'Importance',
}}], {{
  ...layout_base,
  xaxis: {{ ...layout_base.xaxis, title: 'Importance Score' }},
  yaxis: {{ ...layout_base.yaxis, automargin: true }},
  margin: {{ l:240, r:20, t:20, b:60 }},
  height: 520,
}}, config);
</script>
</body>
</html>"""

out_path = os.path.join(DASH_DIR, 'index.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"[4/4] Dashboard written to: {out_path}")
print(f"\n✅ Dashboard complete!")
print(f"   Open: {out_path}")
