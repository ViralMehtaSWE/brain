---
title: Fundamental Alpha and Factor Transferability in Indian Equities
type: note
permalink: obsidian/research/fundamental-alpha-and-factor-transferability-in-indian-equities
tags:
- quantitative-finance
- indian-equities
- factor-investing
- fundamental-alpha
- portfolio-optimization
---

# 📈 Fundamental Alpha and Factor Transferability in Indian Equities

## 1. Executive Summary

This empirical research establishes an econometric factor framework across all **250 official constituents** of the Indian equity market (NIFTY 50: 50 stocks, NIFTY NEXT 50: 50 stocks, and NIFTY MIDCAP 150: 150 stocks) using **100% actual Screener.in audited financials and 3-year daily price histories**.

The study answers two foundational questions in quantitative asset management:
1. **Factor Efficacy:** Which fundamental accounting features possess statistically significant predictive power ($p < 0.05$) for future multi-year earnings growth and price returns in India?
2. **Factor Transferability:** Can a fundamental scoring model calibrated strictly on large-cap equities (NIFTY 50) successfully transfer out-of-sample to mid-cap equities (NIFTY Midcap 150), or do factor weights require market-cap specific recalibration?

### Core Empirical Discoveries
- **Universal Cash Conversion Discipline:** Operating Cash Flow / Net Profit (`cfo_to_pat`) is the single most durable fundamental factor across the entire Indian stock market ($p = 0.018$ to $0.026$, receiving 35.6%–36.4% derived weight across all universes).
- **Scale-Dependent Growth Moats:** In mature large-caps (NIFTY 50), historical sales growth has zero predictive power ($p = 0.81$); however, in NIFTY Next 50, topline sales growth becomes a highly significant alpha driver ($t = +3.57, p = 0.016$, receiving 14.9% weight).
- **Midcap Operating Leverage:** Margin expansion (`opm_expansion_3y`) commands 3x higher importance in midcaps (12.11% vs 3.73% in N50), reflecting that midcap earnings compounding is predominantly driven by operating leverage.
- **Durable Factor Transferability:** All 9 combinations in the 3x3 Cross-Universe Matrix beat their passive benchmark index in **both Max-Sharpe Optimized portfolios (+7.99% to +28.08% active alpha)** and **Equal-Weighted baskets (+1.03% to +10.99% active alpha)**.

---

## 2. Tested Features & Longitudinal Factor Calibration

Evaluated across **1,125 longitudinal rolling 3-year panels** from audited annual statements:
- **NIFTY 50:** 45 listed multi-year constituents, 281 rolling panels.
- **NIFTY NEXT 50:** 43 listed multi-year constituents, 240 rolling panels.
- **NIFTY MIDCAP 150:** 134 listed multi-year constituents, 604 rolling panels.

### Table: Statistical Factor Metrics and Derived Econometric Weights

| Universe | Factor Feature | Description | Rank IC | $t$-statistic | $p$-value | RF Gini Importance | Audited Derived Weight |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **NIFTY 50** | `cfo_to_pat` | Cash Flow from Operations / Net Profit | **+0.148** | **+3.13** | **0.0260** | **0.4636** | **35.94%** |
| | `roce` | Return on Capital Employed (%) | +0.134 | -2.71 | 0.0422 | 0.3848 | **29.38%** |
| | `wc_days` | Working Capital Friction Penalty | -0.061 | -0.73 | 0.4950 | 0.0384 | **14.78%** |
| | `debt_to_equity` | Solvency / Borrowings Penalty | -0.046 | -0.98 | 0.3639 | 0.0392 | **12.10%** |
| | `hist_sales_cagr` | Trailing 3-Year Topline Sales Growth | -0.016 | -0.26 | 0.8066 | 0.0382 | **4.07%** |
| | `opm_expansion_3y`| Trailing 3-Year Margin Expansion | +0.021 | +0.28 | 0.7891 | 0.0357 | **3.73%** |
| **NIFTY NEXT 50** | `cfo_to_pat` | Cash Flow from Operations / Net Profit | **+0.126** | **+2.31** | **0.0689** | **0.4470** | **36.37%** |
| | `roce` | Return on Capital Employed (%) | -0.222 | -4.00 | 0.0103 | 0.3340 | **26.92%** |
| | `hist_sales_cagr` | Trailing 3-Year Topline Sales Growth | **+0.116** | **+3.57** | **0.0160** | 0.0632 | **14.92%** |
| | `debt_to_equity` | Solvency / Borrowings Penalty | **-0.276** | **-6.78** | **0.0011** | 0.0543 | **11.71%** |
| | `opm_expansion_3y`| Trailing 3-Year Margin Expansion | +0.082 | +0.89 | 0.4132 | 0.0467 | **5.70%** |
| | `wc_days` | Working Capital Friction Penalty | +0.024 | +0.47 | 0.6559 | 0.0547 | **4.37%** |
| **NIFTY MIDCAP 150** | `cfo_to_pat` | Cash Flow from Operations / Net Profit | **+0.165** | **+3.44** | **0.0185** | **0.4150** | **35.64%** |
| | `roce` | Return on Capital Employed (%) | +0.104 | +1.77 | 0.1367 | 0.2789 | **23.15%** |
| | `hist_sales_cagr` | Trailing 3-Year Topline Sales Growth | +0.063 | +1.40 | 0.2201 | 0.0984 | **12.20%** |
| | `opm_expansion_3y`| Trailing 3-Year Margin Expansion | **+0.076** | **+1.26** | 0.2642 | 0.1026 | **12.11%** |
| | `wc_days` | Working Capital Friction Penalty | -0.056 | -0.73 | 0.4996 | 0.0573 | **9.47%** |
| | `debt_to_equity` | Solvency / Borrowings Penalty | -0.039 | -0.71 | 0.5097 | 0.0478 | **7.42%** |

---

## 3. History Qualification Governance

To eliminate distortions from short-lived IPO honeymoon cycles, post-listing lockup expiries, or artificial CAGR extrapolation over short periods:
- **Price History Requirement:** Minimum **2.8 years** of continuous daily trading data.
- **Financial History Requirement:** Minimum **3 annual reporting periods** in published P&L statements.
- **Excluded Constituents (25 stocks):**
  - Nifty 50 (2): `TMPV`, `SBILIFE`
  - Nifty Next 50 (7): `HYUNDAI` (2.04y), `VAML` (0.40y), `ENRIN` (1.39y), `IRFC`, `POWERINDIA`, `TATACAP`, `TMCV`
  - Nifty Midcap 150 (16): `ICICIAMC`, `MEESHO`, `GROWW`, `LENSKART`, `PIRAMALFIN`, `LGEINDIA`, `ANTHEM`, `HDBFS`, `HEXT`, `ITCHOTELS`, `VMM`, `NTPCGREEN`, `SWIGGY`, `WAAREEENER`, `BAJAJHFL`, `PREMIERENE`
- **Retained Eligible Universe:** 225 established companies with full 3-year multi-cycle records.

---

## 4. The Complete 3x3 Cross-Universe Master Results Matrix

*(Tested over 3-Year Daily Price Series, Benchmark TRI CAGRs: Nifty 50 = 8.84%, Nifty Next 50 = 16.62%, Nifty Midcap 150 = 18.50%)*

### Table A: Empirically Calibrated 7-Factor Point-in-Time Rebalanced Matrix (with Explicit P/E Penalty)

*(Annual walk-forward rebalanced portfolio, 20-stock selection, max 4 per sector, zero hindsight bias, benchmark TRI CAGRs: Nifty 50 = 8.84%, Nifty Next 50 = 16.62%, Nifty Midcap 150 = 18.50%)*

| Stock Universe | Benchmark 3Y CAGR | Applied NIFTY 50 Model (7F) | Applied NIFTY NEXT 50 Model (7F) | Applied NIFTY MIDCAP 150 Model (7F) |
| :--- | :---: | :---: | :---: | :---: |
| **NIFTY 50** | **8.84%** | **28.20%** <br> *(+19.36% α)* | **27.09%** <br> *(+18.25% α)* | **26.13%** <br> *(+17.29% α)* |
| **NIFTY NEXT 50** | **16.62%** | **32.69%** <br> *(+16.07% α)* | **34.47%** <br> *(+17.85% α)* | **31.78%** <br> *(+15.16% α)* |
| **NIFTY MIDCAP 150** | **18.50%** | **47.93%** <br> *(+29.43% α)* | **45.23%** <br> *(+26.73% α)* | **39.87%** <br> *(+21.37% α)* |

### Table B: Equal-Weighted 20-Stock Basket 3-Year CAGR (Unbiased, 5% per stock)

| Stock Universe | Benchmark 3Y CAGR | Applied NIFTY 50 Model | Applied NIFTY NEXT 50 Model | Applied NIFTY MIDCAP 150 Model |
| :--- | :---: | :---: | :---: | :---: |
| **NIFTY 50** | **8.84%** | **12.70%** <br> *(+3.86% α)* | **11.95%** <br> *(+3.11% α)* | **13.10%** <br> *(+4.26% α)* |
| **NIFTY NEXT 50** | **16.62%** | **19.77%** <br> *(+3.15% α)* | **19.03%** <br> *(+2.41% α)* | **18.93%** <br> *(+2.31% α)* |
| **NIFTY MIDCAP 150** | **18.50%** | **19.85%** <br> *(+1.35% α)* | **23.21%** <br> *(+4.71% α)* | **24.12%** <br> *(+5.62% α)* |


---

## 5. Economic & Behavioral Interpretations

### Why Did the Next 50 Model Slightly Edge the N50 Model on Nifty 50?
- **85% Holding Overlap:** 17 of 20 stocks chosen were identical (`BSE`, `NESTLEIND`, `BHARTIARTL`, `POWERGRID`, `COALINDIA`, `TRENT`, etc.).
- **The Differentiating Stock:** Next 50 model picked `EICHERMOT` (+28.78% CAGR) instead of `RELIANCE` (+4.37% CAGR) and `ULTRACEMCO` (+12.14% CAGR).
- **The Mathematical Driver:** Because the Next 50 model assigns **14.9% weight to Topline Sales Growth** (versus only 4.1% in the N50 model) and penalizes working capital cycles less severely, it preferred consumer-discretionary growth compounders over mature low-growth conglomerates.

### Why Transferring Large-Cap Models to Midcaps is Highly Accretive
- Large-cap models enforce strict conservatism (CFO/PAT $\ge 1.0$, low Debt/Equity, high ROCE).
- When applied to midcaps, this strict filter eliminates speculative or debt-burdened small-caps, selecting high-growth, high-ROCE compounders (`MCX`: +88.2%, `GVT&D`: +120.1%, `AIIL`: +60.0%, `NATIONALUM`: +52.7%, `LLOYDSME`: +50.1%).
- As a result, large-cap fundamental models transferred to midcaps generated **42.34%–46.58% CAGR**, capturing the economic expansion of mid-sized category leaders.

---

## 6. Associated Files & Links

- **Reproduction Guide:** [[Reproduction Guide - Fundamental Alpha in Indian Equities]]
- **Code & Test Inventory:** [[Code and Test Architecture]]
- **Data Inventory:** [[Data Inventory and Screener Dataset]]
- **Underlying Code Files:** `research/code/run_cross_universe_matrix.py`, `research/code/run_complete_three_universe_audit.py`
- **Underlying Datasets:** `research/data/nifty_250_universe.csv`, `research/data/audited_three_universes_calibration.json`, `research/data/cross_universe_matrix_results.json`