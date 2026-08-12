"""
run_all.py - Master pipeline runner
Mining Process Quality Prediction Project
"""
import subprocess
import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR  = os.path.join(BASE_DIR, "src")

steps = [
    ("01_eda.py",                "EDA - Exploratory Data Analysis"),
    ("02_feature_engineering.py","Feature Engineering"),
    ("03_train_models.py",       "Model Training (3 Experiments)"),
    ("04_generate_dashboard.py", "Dashboard Generation"),
]

print("\n" + "=" * 65)
print("  MINING QUALITY PREDICTION -- FULL PIPELINE")
print("=" * 65 + "\n")

total_start = time.time()
for script, label in steps:
    path = os.path.join(SRC_DIR, script)
    print("\n" + "-" * 65)
    print(f"  STEP: {label}")
    print("-" * 65)
    t0 = time.time()
    result = subprocess.run([sys.executable, path], capture_output=False, text=True)
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"\n[FAILED] Step: {script}  (exit code {result.returncode})")
        sys.exit(1)
    print(f"\n  [OK] Completed in {elapsed:.1f}s")

total = time.time() - total_start
print("\n" + "=" * 65)
print(f"  ALL STEPS COMPLETE  ({total:.0f}s total)")
dash = os.path.join(BASE_DIR, "dashboard", "index.html")
print(f"\n  Dashboard -> {dash}")
print("=" * 65 + "\n")
