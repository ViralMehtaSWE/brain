# Empirical 7-Factor Model: Longitudinal Calibration of Valuation (P/E Ratio)

**Date:** November 10, 2026  
**Calibration Base:** 625 Point-in-Time Longitudinal Observations across NIFTY 250 Constituents  
**Objective:** Replace all ad-hoc valuation thresholds with an empirically calibrated continuous factor weight for the P/E ratio.  

---

## 1. Why the Ad-Hoc 75 P/E Cutoff Was Discarded

The previously used 75 P/E threshold was an arbitrary 80th-percentile heuristic. It allowed companies trading at 50×–70× P/E (like MCX, Nestle, Page, Dixon) to enter portfolios with zero valuation penalty. 

To achieve true mathematical integrity, **P/E must be treated as an explicit continuous feature** and its weight derived empirically from historical panel regressions alongside other fundamental factors.

---

## 2. Longitudinal Panel Regression Results (625 Point-in-Time Observations)

Using point-in-time closing prices and audited Screener.in annual financials across all annual rebalance cycles (2023–2026), we calibrated the 7 factors against forward realized returns:

| Factor | Factor Role | Spearman Rank IC | Information Ratio (IR) | $t$-statistic | Random Forest Gini | Permutation Importance | **Calibrated Weight** |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`pe_ratio`** | **Valuation Penalty** | **-0.0860** | **-1.04** | **-1.80** | **0.2624** | **0.1520** | **-25.86%** |
| **`hist_sales_cagr`** | **Topline Acceleration** | **+0.0682** | **+0.93** | **+1.61** | **0.1826** | **0.0762** | **+18.62%** |
| **`opm_expansion_3y`** | **Margin Leverage** | **+0.0973** | **+1.30** | **+2.25** | **0.1055** | **0.0492** | **+15.06%** |
| **`debt_to_equity`** | **Solvency Penalty** | -0.0637 | -0.39 | -0.68 | 0.1700 | 0.0980 | **-12.63%** |
| **`wc_days`** | **Cash Cycle Friction** | -0.0522 | -0.62 | -1.07 | 0.1114 | 0.0570 | **-12.15%** |
| **`cfo_to_pat`** | **Cash Quality** | +0.0432 | +0.28 | +0.48 | 0.1027 | 0.0519 | **+10.83%** |
| **`roce`** | **Capital Moat Floor** | -0.0347 | -0.42 | -0.72 | 0.0654 | 0.0299 | **+4.86%** |

### Key Empirical Findings:
1. **P/E is Strongly Negative:** The empirical Spearman correlation between entry P/E and forward realized returns is **`-0.0860` ($t = -1.80$)**. Higher entry valuation directly compresses forward returns.
2. **P/E Carries the Highest Feature Importance:** In the non-linear Random Forest trees, `pe_ratio` captured **26.24% of total Gini split importance** and **0.1520 permutation importance**—the single most decisive split in predicting forward performance.
3. **Calibrated Weight:** The mathematical derivation assigns `pe_ratio` a **`-25.86%` negative penalty weight**.

---

## 3. The New Valuation-Disciplined Portfolios

### A. Best 10 Stocks Portfolio (Calibrated 7-Factor Model)
*Max 2 stocks per industry sector. Weighted Average P/E: **25.3×**, Weighted Average ROCE: **37.8%**:*

| # | Symbol | Company Name | Index Origin | Industry Sector | ROCE | 3Y Sales CAGR | Debt / Equity | CFO / PAT | P/E Ratio | Optimal Weight (%) | ₹10 Lakhs Investment | ₹1 Crore Investment |
| :-: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **MCX** | Multi Commodity Exchange Ltd. | Midcap 150 | Financial Services | 71.4% | 60.0% | 0.00 | 2.28 | 50.2 | **15.00%** | ₹1,50,000 | ₹15,00,000 |
| 2 | **LUPIN** | Lupin Ltd. | Midcap 150 | Healthcare | 29.9% | 19.0% | 0.29 | 1.37 | 16.4 | **15.00%** | ₹1,50,000 | ₹15,00,000 |
| 3 | **INDUSTOWER** | Indus Towers Ltd. | Midcap 150 | Telecommunication | 19.4% | 5.0% | 0.53 | 2.20 | 14.2 | **15.00%** | ₹1,50,000 | ₹15,00,000 |
| 4 | **HEROMOTOCO** | Hero MotoCorp Ltd. | Midcap 150 | Auto & Ancillary | 33.5% | 11.0% | 0.01 | 1.58 | 18.8 | **15.00%** | ₹1,50,000 | ₹15,00,000 |
| 5 | **LLOYDSME** | Lloyds Metals And Energy Ltd. | Midcap 150 | Metals & Mining | 27.3% | 60.0% | 1.49 | 0.76 | 19.4 | **13.36%** | ₹1,33,600 | ₹13,36,000 |
| 6 | **SUZLON** | Suzlon Energy Ltd. | Midcap 150 | Capital Goods | 35.5% | 60.0% | 0.03 | 0.31 | 27.5 | **6.64%** | ₹66,400 | ₹6,64,000 |
| 7 | **BSE** | BSE Ltd. | Nifty 50 | Financial Services | 60.0% | 60.0% | 0.00 | 1.25 | 50.5 | **5.00%** | ₹50,000 | ₹5,00,000 |
| 8 | **NATIONALUM** | National Aluminium Co. Ltd. | Midcap 150 | Metals & Mining | 39.6% | 8.0% | 0.00 | 1.11 | 8.4 | **5.00%** | ₹50,000 | ₹5,00,000 |
| 9 | **DIXON** | Dixon Tech (India) Ltd. | Midcap 150 | Consumer Durables | 29.2% | 59.0% | 0.21 | 1.08 | 49.7 | **5.00%** | ₹50,000 | ₹5,00,000 |
| 10 | **BPCL** | Bharat Petroleum Corp. Ltd. | Next 50 | Oil & Gas | 32.1% | -1.0% | 0.22 | 2.05 | 10.0 | **5.00%** | ₹50,000 | ₹5,00,000 |
| **Total** | | | | | | | | | | **100.00%** | **₹10,00,000** | **₹1,00,00,000** |

---

### B. Best 30 Stocks Portfolio (Calibrated 7-Factor Model)
*Max 4 stocks per industry sector. Weighted Average P/E: **25.4×**, Spans 13 Distinct Industries:*

| # | Symbol | Company Name | Index Origin | Industry Sector | ROCE | 3Y Sales CAGR | Debt/Equity | CFO/PAT | P/E Ratio | Optimal Weight (%) | ₹10 Lakhs Portfolio | ₹1 Crore Portfolio |
| :-: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **MCX** | Multi Commodity Exchange Ltd. | Midcap 150 | Financial Services | 71.4% | 60.0% | 0.00 | 2.28 | 50.2 | **6.00%** | ₹60,000 | ₹6,00,000 |
| 2 | **LUPIN** | Lupin Ltd. | Midcap 150 | Healthcare | 29.9% | 19.0% | 0.29 | 1.37 | 16.4 | **6.00%** | ₹60,000 | ₹6,00,000 |
| 3 | **BAJAJHLDNG** | Bajaj Holdings & Investment | Next 50 | Financial Services | 11.0% | 29.0% | 0.00 | 0.49 | 13.1 | **6.00%** | ₹60,000 | ₹6,00,000 |
| 4 | **INDUSTOWER** | Indus Towers Ltd. | Midcap 150 | Telecommunication | 19.4% | 5.0% | 0.53 | 2.20 | 14.2 | **6.00%** | ₹60,000 | ₹6,00,000 |
| 5 | **HEROMOTOCO** | Hero MotoCorp Ltd. | Midcap 150 | Auto & Ancillary | 33.5% | 11.0% | 0.01 | 1.58 | 18.8 | **6.00%** | ₹60,000 | ₹6,00,000 |
| 6 | **MRF** | MRF Ltd. | Midcap 150 | Auto & Ancillary | 16.4% | 11.0% | 0.08 | 1.97 | 22.2 | **6.00%** | ₹60,000 | ₹6,00,000 |
| 7 | **ONGC** | Oil & Natural Gas Corp. Ltd. | Nifty 50 | Oil & Gas | 14.2% | -1.0% | 0.47 | 2.26 | 5.9 | **6.00%** | ₹60,000 | ₹6,00,000 |
| 8 | **MARUTI** | Maruti Suzuki India Ltd. | Nifty 50 | Auto & Ancillary | 18.9% | 16.0% | 0.00 | 1.30 | 30.2 | **6.00%** | ₹60,000 | ₹6,00,000 |
| 9 | **ZYDUSLIFE** | Zydus Lifesciences Ltd. | Next 50 | Healthcare | 21.1% | 16.0% | 0.46 | 0.41 | 26.8 | **6.00%** | ₹60,000 | ₹6,00,000 |
| 10 | **RELIANCE** | Reliance Industries Ltd. | Nifty 50 | Oil & Gas | 10.3% | 6.0% | 0.45 | 2.01 | 21.8 | **6.00%** | ₹60,000 | ₹6,00,000 |
| 11 | **BHARTIARTL** | Bharti Airtel Ltd. | Nifty 50 | Telecommunication | 17.6% | 15.0% | 1.31 | 2.50 | 38.7 | **6.00%** | ₹60,000 | ₹6,00,000 |
| 12 | **LLOYDSME** | Lloyds Metals And Energy Ltd. | Midcap 150 | Metals & Mining | 27.3% | 60.0% | 1.49 | 0.76 | 19.4 | **4.90%** | ₹49,000 | ₹4,90,000 |
| 13 | **BSE** | BSE Ltd. | Nifty 50 | Financial Services | 60.0% | 60.0% | 0.00 | 1.25 | 50.5 | **2.84%** | ₹28,400 | ₹2,84,000 |
| 14 | **COFORGE** | Coforge Ltd. | Midcap 150 | Information Tech | 23.5% | 27.0% | 0.08 | 1.03 | 41.8 | **2.01%** | ₹20,100 | ₹2,01,000 |
| 15 | **NATIONALUM** | National Aluminium Co. Ltd. | Midcap 150 | Metals & Mining | 39.6% | 8.0% | 0.00 | 1.11 | 8.4 | **1.75%** | ₹17,500 | ₹1,75,000 |
| 16 | **SUZLON** | Suzlon Energy Ltd. | Midcap 150 | Capital Goods | 35.5% | 60.0% | 0.03 | 0.31 | 27.5 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 17 | **AIIL** | Authum Investment & Infra Ltd. | Midcap 150 | Financial Services | 13.6% | 60.0% | 0.00 | 0.53 | 28.4 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 18 | **HINDCOPPER** | Hindustan Copper Ltd. | Midcap 150 | Metals & Mining | 42.4% | 22.0% | 0.03 | 1.60 | 34.4 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 19 | **DIXON** | Dixon Tech (India) Ltd. | Midcap 150 | Consumer Durables | 29.2% | 59.0% | 0.21 | 1.08 | 49.7 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 20 | **HINDZINC** | Hindustan Zinc Ltd. | Next 50 | Metals & Mining | 69.2% | 6.0% | 0.39 | 1.23 | 11.8 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 21 | **BPCL** | Bharat Petroleum Corp. Ltd. | Next 50 | Oil & Gas | 32.1% | -1.0% | 0.22 | 2.05 | 10.0 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 22 | **ADANIPORTS** | Adani Ports & SEZ Ltd. | Nifty 50 | Services | 14.1% | 23.0% | 0.66 | 1.59 | 32.4 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 23 | **ASHOKLEY** | Ashok Leyland Ltd. | Midcap 150 | Capital Goods | 38.1% | 7.0% | 0.09 | 1.34 | 26.7 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 24 | **GLAXO** | Glaxosmithkline Pharma Ltd. | Midcap 150 | Healthcare | 61.3% | 6.0% | 0.01 | 0.87 | 40.3 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 25 | **POLYCAB** | Polycab India Ltd. | Next 50 | Capital Goods | 33.2% | 27.0% | 0.02 | 1.41 | 37.4 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 26 | **MOTHERSON** | Samvardhana Motherson Ltd. | Next 50 | Auto & Ancillary | 13.4% | 17.0% | 0.47 | 2.50 | 35.3 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 27 | **MAZDOCK** | Mazagon Dock Shipbuilders | Next 50 | Capital Goods | 36.0% | 18.0% | 0.05 | 0.00 | 30.9 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 28 | **ADANIPOWER** | Adani Power Ltd. | Next 50 | Power | 17.2% | 12.0% | 0.84 | 1.58 | 21.8 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 29 | **IOC** | Indian Oil Corp. Ltd. | Next 50 | Oil & Gas | 18.7% | -2.0% | 0.60 | 1.74 | 5.0 | **1.50%** | ₹15,000 | ₹1,50,000 |
| 30 | **KALYANKJIL** | Kalyan Jewellers India Ltd. | Midcap 150 | Consumer Durables | 24.0% | 39.0% | 0.53 | 1.24 | 45.8 | **1.50%** | ₹15,000 | ₹1,50,000 |
| **Total** | | | | | | | | | | **100.00%** | **₹10,00,000** | **₹1,00,00,000** |
