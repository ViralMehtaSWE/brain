---
title: Data Inventory and Screener Dataset
type: note
permalink: obsidian/research/data-inventory-and-screener-dataset
tags:
- quantitative-finance
- data-engineering
- financial-datasets
- screener-in
- indian-equities
---

# 📊 Data Inventory: Indian Equities Fundamental & Price Dataset

## 1. Overview

All raw, interim, and final datasets used in this research are stored in the Obsidian vault under:
`~/.brain/brain/research/data/`

The data originates exclusively from authoritative Indian equity market sources:
- **NSE India:** Official index constituent lists and Total Returns Index (TRI) benchmark histories.
- **Screener.in:** Audited multi-year financial statements (P&L, Balance Sheet, Cash Flow, Ratios) and daily closing price histories.

---

## 2. Core Datasets

### A. Universe Constituent Master (`nifty_250_universe.csv`)
- **Path:** `research/data/nifty_250_universe.csv`
- **Total Records:** 250 constituents
- **Schema:**
  - `Company Name`: Full registered legal name of the entity.
  - `Industry`: Official NSE sector / industry classification (e.g. `IT - Software`, `Automobiles`, `Capital Goods`).
  - `Symbol`: Authoritative NSE trading ticker symbol.
  - `Series`: Market trading segment (`EQ` for ordinary equity).
  - `ISIN Code`: 12-character International Securities Identification Number.
  - `Benchmark_Index`: Corresponding index universe (`NIFTY 50`, `NIFTY NEXT 50`, `NIFTY MIDCAP 150`).

### B. Econometric Calibration Results (`audited_three_universes_calibration.json`)
- **Path:** `research/data/audited_three_universes_calibration.json`
- **Scope:** 1,125 longitudinal rolling 3-year observation windows across 222 multi-year companies.
- **Contents:**
  - `factor_statistics`: Rank IC, IC standard deviation, Information Ratio, $t$-statistic, $p$-value for all 6 features.
  - `machine_learning_importances`: Random Forest MDI Gini importance and feature rankings.
  - `unrounded_weights`: Exact floating-point weights derived from empirical signal power.
  - `rounded_weights`: Production-ready allocations strictly summing to 100.0%.

### C. 3x3 Cross-Universe Matrix Results (`cross_universe_matrix_results.json`)
- **Path:** `research/data/cross_universe_matrix_results.json`
- **Scope:** Complete evaluation of all 9 universe-model combinations.
- **Per-Cell Structure:**
  - `selected_stocks`: Ordered list of 20 selected equities meeting sector and history criteria.
  - `stock_cagrs`: Realized 3-year buy-and-hold CAGR for every individual constituent.
  - `ew_cagr`: Equal-weighted portfolio CAGR (5.0% per stock).
  - `opt_cagr`: Maximum-Sharpe optimized portfolio CAGR.
  - `opt_vol`: Annualized daily portfolio volatility.
  - `opt_sharpe`: Realized portfolio Sharpe ratio ($R_f = 7\%$).
  - `bm_cagr`: Official benchmark 3Y CAGR.
  - `active_alpha`: Net outperformance over benchmark.
  - `beats_benchmark`: Boolean verification flag.

### D. Verified Daily Price Series (`research/data/prices/*.csv`)
- **Path:** `research/data/prices/`
- **Total Files:** 247 constituent CSV files.
- **Format:** `date,price` (weekly/daily closing prices).
- **Date Range:** November 2023 to November 2026 (~158 weekly observation points for mature constituents).
- **Integrity Status:** 100% reconciled against Screener.in live HTML prices via `fix_all_prices_and_cids.py`.

---

## 3. Data Governance & Hygiene Standards

1. **Zero Hallucination Guarantee:** No synthetic data, proxy substitutions, or simulated financial numbers are used. If an unlisted entity (`TMPV`, `TATACAP`) lacks live exchange prices, it is recorded as missing and excluded via the History Qualification Gate.
2. **Winsorization:** Extreme outlier ratios are winsorized to the 2nd and 98th percentiles within each index universe to prevent distortion from distress-level accounting noise.
3. **P/E Multiples:** Capped at 150x with a valuation drag penalty applied for stocks trading above 75x P/E.

---

## 4. Associated Notes

- Main Research Paper: [[Fundamental Alpha and Factor Transferability in Indian Equities]]
- Reproduction Protocol: [[Reproduction Guide - Fundamental Alpha in Indian Equities]]
- Code & Test Architecture: [[Code and Test Architecture]]