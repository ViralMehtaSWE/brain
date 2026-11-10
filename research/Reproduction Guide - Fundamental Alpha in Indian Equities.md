---
title: Reproduction Guide - Fundamental Alpha in Indian Equities
type: note
permalink: obsidian/research/reproduction-guide-fundamental-alpha-in-indian-equities
tags:
- quantitative-finance
- reproduction-guide
- methodology
- verification-protocol
- backtest
---

# 🔁 Reproduction Guide: Fundamental Alpha and Factor Transferability in Indian Equities

## 1. System Requirements & Environment Setup

This research is 100% reproducible on macOS / Linux using Python 3.9+.

### Dependencies
```bash
python3 -m venv ~/investment/venv
source ~/investment/venv/bin/activate
pip install numpy pandas scipy scikit-learn
```

### Directory Structure
Ensure the repository files are located at:
```
~/.brain/brain/research/
├── code/
│   ├── run_complete_three_universe_audit.py
│   ├── run_cross_universe_matrix.py
│   ├── fix_all_prices_and_cids.py
│   └── test_*.py (9 test suites)
├── data/
│   ├── nifty_250_universe.csv
│   ├── audited_three_universes_calibration.json
│   ├── cross_universe_matrix_results.json
│   └── prices/ (247 constituent daily price CSVs)
```

---

## 2. Step-by-Step Reproduction Protocol

### Step 1: Universe Constitution & Verification
Verify that `nifty_250_universe.csv` contains all 250 constituents across the three official NSE indices:
```bash
python3 -c "
import pandas as pd
df = pd.read_csv('~/.brain/brain/research/data/nifty_250_universe.csv')
print(df['Benchmark_Index'].value_counts())
"
```
**Expected Output:**
```
NIFTY MIDCAP 150    150
NIFTY NEXT 50        50
NIFTY 50             50
Name: Benchmark_Index, dtype: int64
```

### Step 2: History Qualification Gate (Filtering Recent IPOs)
The governance rule requires at least **2.8 years of continuous trading price history** and **3 annual P&L reporting periods**:
- Run the check:
```bash
python3 -c "
import os, pandas as pd
cache = '~/.brain/brain/research/data/prices'
pfs = [f for f in os.listdir(cache) if f.endswith('_price.csv')]
print(f'Total price CSVs: {len(pfs)}')
"
```
Any company with $< 2.8$ years of daily trading history is automatically excluded upfront from candidate portfolio ranking (exactly 25 stocks excluded, 225 eligible).

### Step 3: Run Full Econometric Panel Calibration
To re-derive the factor correlation matrix, Rank IC, $t$-statistics, $p$-values, and Random Forest feature importances across all 1,125 rolling panels:
```bash
python3 ~/.brain/brain/research/code/run_complete_three_universe_audit.py
```
This script parses the longitudinal financial tables and outputs `audited_three_universes_calibration.json`.

### Step 4: Run the 3x3 Cross-Universe Transferability Engine
To execute the 3x3 backtest and compute realized 3-year CAGRs, portfolio volatility, Sharpe ratios, and active alphas:
```bash
python3 ~/.brain/brain/research/code/run_cross_universe_matrix.py
```

**Expected Console Output:**
```
===============================================================================================
RUNNING 3x3 CROSS-UNIVERSE FACTOR TRANSFERABILITY EXPERIMENT
===============================================================================================
Universe: NIFTY 50         | Model: NIFTY 50 Model         | Opt CAGR:  20.62% | EW CAGR:  10.92% | Sharpe: 0.38 | Alpha: +11.78% [BEATS BENCHMARK]
Universe: NIFTY 50         | Model: NIFTY NEXT 50 Model    | Opt CAGR:  22.13% | EW CAGR:  11.95% | Sharpe: 0.43 | Alpha: +13.29% [BEATS BENCHMARK]
Universe: NIFTY 50         | Model: NIFTY MIDCAP 150 Model | Opt CAGR:  22.71% | EW CAGR:  13.10% | Sharpe: 0.44 | Alpha: +13.87% [BEATS BENCHMARK]
Universe: NIFTY NEXT 50    | Model: NIFTY 50 Model         | Opt CAGR:  24.61% | EW CAGR:  17.65% | Sharpe: 0.42 | Alpha:  +7.99% [BEATS BENCHMARK]
Universe: NIFTY NEXT 50    | Model: NIFTY NEXT 50 Model    | Opt CAGR:  26.07% | EW CAGR:  18.26% | Sharpe: 0.45 | Alpha:  +9.45% [BEATS BENCHMARK]
Universe: NIFTY NEXT 50    | Model: NIFTY MIDCAP 150 Model | Opt CAGR:  26.72% | EW CAGR:  19.02% | Sharpe: 0.46 | Alpha: +10.10% [BEATS BENCHMARK]
Universe: NIFTY MIDCAP 150 | Model: NIFTY 50 Model         | Opt CAGR:  42.34% | EW CAGR:  27.35% | Sharpe: 0.83 | Alpha: +23.84% [BEATS BENCHMARK]
Universe: NIFTY MIDCAP 150 | Model: NIFTY NEXT 50 Model    | Opt CAGR:  46.58% | EW CAGR:  29.49% | Sharpe: 0.80 | Alpha: +28.08% [BEATS BENCHMARK]
Universe: NIFTY MIDCAP 150 | Model: NIFTY MIDCAP 150 Model | Opt CAGR:  46.42% | EW CAGR:  29.14% | Sharpe: 0.80 | Alpha: +27.92% [BEATS BENCHMARK]
```

### Step 5: Execute the Master Test Suite (93 Tests)
Run the automated unit test suite covering data integrity, mathematical constraints, and outperformance assertions:
```bash
python3 -m unittest discover -s ~/.brain/brain/research/code/ -p "test_*.py"
```

**Expected Test Output:**
```
.............................................................................................
----------------------------------------------------------------------
Ran 93 tests in 41.5s

OK
```

---

## 3. Mathematical Verification Criteria & Bounds

When verifying your run against this guide:
1. **Weight Conservation:** For all portfolios, $\sum_{i=1}^{20} w_i \equiv 1.000000 \pm 10^{-6}$.
2. **Position Limits:** Each stock allocation must satisfy $0.025 \le w_i \le 0.100$.
3. **Sector Diversification:** No single industry may hold more than 4 stocks in the 20-stock portfolio.
4. **CAGR Consistency:** Realized CAGRs must match the reference matrix within $\pm 0.05\%$ (accounting for minor float rounding in SLSQP solver convergence).
5. **Universal Alpha:** Active alpha ($R_{\text{port}} - R_{\text{bench}}$) must be strictly positive across all 9 combinations in both Optimized and Equal-Weighted modes.

---

## 4. Associated Notes

- Main Research Paper: [[Fundamental Alpha and Factor Transferability in Indian Equities]]
- Architecture & Test Specifications: [[Code and Test Architecture]]
- Dataset Documentation: [[Data Inventory and Screener Dataset]]