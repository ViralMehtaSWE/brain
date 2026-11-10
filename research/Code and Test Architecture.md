---
title: Code and Test Architecture
type: note
permalink: obsidian/research/code-and-test-architecture
tags:
- quantitative-finance
- code-architecture
- test-suite
- unit-testing
- data-pipeline
---

# 🏗️ Code and Test Architecture: Fundamental Alpha Engine

## 1. Overview

The empirical research codebase comprises **32 Python files** organized into a modular pipeline covering data ingestion, econometric factor calibration, portfolio optimization, cross-universe matrix backtesting, and automated unit testing.

All files are stored in the Obsidian vault at:
`~/.brain/brain/research/code/`

---

## 2. Pipeline Components & Script Inventory

### Layer A: Data Ingestion & Hygiene
- **[`fix_all_prices_and_cids.py`](research/code/fix_all_prices_and_cids.py):**
  Authoritative reconciliation script. Parses raw Screener.in HTML files to extract authentic company IDs (`data-row-company-id`), audits daily price CSV series against HTML current market prices, and detects/fixes any mapping anomalies (e.g. Maruti Suzuki CID 2023 vs 1961).
- **[`fetch_needed_prices.py`](research/code/fetch_needed_prices.py):**
  Queries the public Screener daily chart API (`https://www.screener.in/api/company/{cid}/chart/?q=Price-DMA50-DMA200-Volume&days=1095`) and writes unadulterated time series to CSV.
- **[`download_universe.py`](research/code/download_universe.py):**
  Extracts official constituent CSVs from NSE India archives for Nifty 50, Nifty Next 50, and Nifty Midcap 150.

### Layer B: Econometric Calibration & Factor Derivation
- **[`run_complete_three_universe_audit.py`](research/code/run_complete_three_universe_audit.py):**
  Constructs multi-year longitudinal panels (1,125 rolling windows) across all 250 constituents. Computes:
  - Spearman Rank Information Coefficient (Rank IC)
  - Time-series Information Ratio (IC IR) and Student's $t$-statistic / $p$-values
  - Random Forest Regressor Gini Mean Decrease in Impurity (MDI)
  - Normalized factor weights combining Rank IC and Random Forest importance.
  Outputs `research/data/audited_three_universes_calibration.json`.

### Layer C: Portfolio Construction & Optimization Engine
- **[`run_cross_universe_matrix.py`](research/code/run_cross_universe_matrix.py):**
  Core 3x3 backtest and transferability engine:
  - Enforces History Qualification Gate ($\ge 2.8$y price, $\ge 3$y P&L).
  - Normalizes factor Z-scores within universe.
  - Applies valuation penalty ($P/E > 75\text{x}$) and sector cap (max 4 per industry).
  - Computes empirical daily covariance matrix $\Sigma$.
  - Executes SLSQP Maximum Sharpe Ratio optimization under constraints ($w_i \in [2.5\%, 10.0\%]$, $\sum w_i = 100\%$).
  - Outputs `research/data/cross_universe_matrix_results.json`.
- **[`portfolio_optimizer.py`](research/code/portfolio_optimizer.py):**
  Stand-alone optimizer module implementing quadratic programming, risk-free rate adjustment ($R_f = 7\%$), and position boundary constraints.

---

## 3. Unit Test Suite (93 Tests, 100% Passing)

The pipeline is verified by **9 test suites** containing 93 comprehensive unit tests:

| Test File | Test Count | Scope & Invariants Tested |
| :--- | :---: | :--- |
| **`test_master_audit_integrity.py`** | 4 | Full 250 constituent presence, longitudinal panel observation sufficiency ($> 200, > 180, > 600$ windows), mathematical weight conservation ($\sum w_f \equiv 1.0$), statistical significance ($p < 0.05$). |
| **`test_cross_universe_matrix.py`** | 5 | All 9 matrix cells beat respective benchmarks in Opt CAGR; all 9 equal-weighted combinations beat benchmark; Midcap universe generates highest absolute returns. |
| **`test_midcap150_complete.py`** | 9 | Midcap 150 portfolio size ($K=20$), position bounds ($[2.5\%, 10.0\%]$), capital conservation, and active outperformance. |
| **`test_nifty50_on_next50.py`** | 5 | Transferability of N50 model to Next 50 universe, active alpha $> 4.0\%$, Sharpe improvement, high stock overlap. |
| **`test_nifty50_on_midcaps.py`** | 7 | Transferability of N50 model to Midcap 150 universe, alpha $> 15.0\%$, sector diversification enforcement. |
| **`test_actual_portfolio.py`** | 15 | Positive semi-definiteness (PSD) of covariance matrices, no NaN eigenvalues, cash allocation strictly sums to ₹10,00,000.00. |
| **`test_nifty250_portfolio.py`** | 19 | Portfolio constraint consistency across portfolio sizes $K \in [15, 20, 25]$, industry exposure caps. |
| **`test_fundamental_alpha.py`** | 24 | Data sanitization, HTML parsing, extreme winsorization (2%–98%), Spearman Rank IC precision, ML Gini sum-to-one property. |
| **`test_portfolio_optimizer.py`** | 5 | SLSQP solver convergence, active betting limits, long-only boundaries. |

### Running the Test Suite
```bash
python3 -m unittest discover -s ~/.brain/brain/research/code/ -p "test_*.py"
```
**Result:** `Ran 93 tests in 41.5s — OK (100% passing)`.

---

## 4. Associated Notes

- Main Research Paper: [[Fundamental Alpha and Factor Transferability in Indian Equities]]
- Reproduction Protocol: [[Reproduction Guide - Fundamental Alpha in Indian Equities]]
- Dataset Documentation: [[Data Inventory and Screener Dataset]]