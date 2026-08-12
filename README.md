# 🏭 Mining Quality Prediction

> Predicting **% Silica Concentrate** impurity in iron ore using Machine Learning on real industrial flotation plant sensor data.

---

## 📋 Problem Statement

A flotation plant separates iron ore from silica (impurity). Silica levels are only measured **once per hour** in a lab — by then it's too late to act. This project uses **real-time sensor data** to predict silica concentration up to **1 hour in advance**, giving engineers time to take corrective action.

## 📊 Dataset

- **737,453** sensor readings over **183 days** (March – September 2017)
- **23 columns**: feed quality, chemical flows, flotation column air flows & levels
- **Target**: `% Silica Concentrate` (Mean: 2.33%, Std: 1.13%)
- Source: [Kaggle — Quality Prediction in a Mining Process](https://www.kaggle.com/datasets/edumagalhaes/quality-prediction-in-a-mining-process)

## 🤖 Tech Stack

| Tool | Purpose |
|---|---|
| Python | Core language |
| XGBoost / LightGBM | Gradient boosted tree models |
| Scikit-learn | Random Forest, metrics |
| Pandas / NumPy | Data processing |
| Plotly | Interactive dashboard |
| Matplotlib / Seaborn | EDA plots |

## 📈 Results

| Experiment | Question | Model | R² |
|---|---|---|---|
| A — Minute-level | Can we predict every minute? | LightGBM | **0.607** ✅ |
| B — 1h ahead | How far ahead? | XGBoost | 0.456 |
| C — No Iron col | Without % Iron Concentrate? | XGBoost | 0.568 ✅ |

## 🔑 Key Findings

1. **Minute-level prediction is feasible** — LightGBM achieves R²=0.61
2. **Reliable up to 1 hour ahead** — beyond 2h, R² drops below 0.32
3. **Works without Iron column** — removing it causes only ΔRMSE=+0.001, enabling lab-independent real-time inference

## 🚀 How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Place the dataset in data/ folder
# data/MiningProcess_Flotation_Plant_Database.csv

# 3. Run the full pipeline
python run_all.py

# 4. Open the dashboard
# Open dashboard/index.html in your browser
```

## 📁 Project Structure

```
mining-quality-prediction/
├── run_all.py                      ← Master runner
├── requirements.txt
├── .gitignore
├── data/                           ← Place CSV here (not in repo)
├── src/
│   ├── 01_eda.py                   ← Exploratory Data Analysis
│   ├── 02_feature_engineering.py  ← Lag & rolling features
│   ├── 03_train_models.py         ← 3 experiments
│   └── 04_generate_dashboard.py   ← HTML dashboard
├── outputs/
│   ├── plots/                      ← 8 EDA & result charts
│   ├── models/                     ← Saved trained models
│   └── results/                    ← Metrics JSON + parquet
└── dashboard/
    └── index.html                  ← Interactive dashboard
```

## 🌱 Business Impact

- ⏱ **Early warning** — 1 hour before lab measurement
- 💰 **Reduces iron loss** to waste tailings
- 🌍 **Environmental benefit** — less ore waste
- 🔬 **Lab-free inference** — works on sensor data alone

---

*Made with Python · XGBoost · LightGBM · Plotly*
