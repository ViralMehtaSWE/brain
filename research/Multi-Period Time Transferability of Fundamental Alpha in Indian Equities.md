---
title: Multi-Period Time Transferability of Fundamental Alpha in Indian Equities
type: note
permalink: obsidian/research/multi-period-time-transferability-of-fundamental-alpha
tags:
- quantitative-finance
- time-transferability
- out-of-sample
- walk-forward
- factor-stability
- indian-equities
---

# ⏳ Multi-Period Time Transferability of Fundamental Alpha in Indian Equities

## 1. Research Motivation & Hypothesis

A central question in quantitative finance is whether econometric factor weights and ranking signals remain valid when **tested across different market regimes and time slices without recalibration**:
- **Null Hypothesis ($H_0$):** Fixed fundamental factor weights overfit to a specific market cycle and degrade or generate negative active alpha during cyclical troughs, market corrections, or low-momentum consolidation phases.
- **Alternative Hypothesis ($H_1$):** Pure fundamental quality factors (Cash Flow Conversion, ROCE, Debt/Equity safeguards) represent structural economic moats that generate durable alpha across bull expansions, valuation compressions, and flat/bearish market regimes.

To test this empirically:
- **Zero Recalibration:** Model features and their exact mathematical weights were held **100% frozen and unchanged**:
  - **Nifty 50 Model:** `cfo_to_pat`: 35.94%, `roce`: 29.38%, `wc_days`: 14.78%, `debt_to_equity`: 12.10%, `hist_sales_cagr`: 4.07%, `opm_expansion_3y`: 3.73%.
  - **Nifty Next 50 Model:** `cfo_to_pat`: 36.37%, `roce`: 26.92%, `hist_sales_cagr`: 14.92%, `debt_to_equity`: 11.71%, `opm_expansion_3y`: 5.70%, `wc_days`: 4.37%.
  - **Nifty Midcap 150 Model:** `cfo_to_pat`: 35.64%, `roce`: 23.15%, `hist_sales_cagr`: 12.20%, `opm_expansion_3y`: 12.11%, `wc_days`: 9.47%, `debt_to_equity`: 7.42%.
- **Zero Synthetic Data:** Evaluated on 100% real Screener.in weekly and daily closing price histories across all 250 constituents.

---

## 2. Tested Time Periods (6 Distinct Market Regimes)

| Period ID | Period Name | Date Span | Macro / Market Regime Characterization |
| :--- | :--- | :---: | :--- |
| **`full_3y`** | Full 3-Year Cycle | Nov 12, 2023 – Nov 09, 2026 | Full Macro Cycle spanning massive bull run, mid-cycle digestion, and late-cycle trough. |
| **`year_1`** | Year 1: Bull Expansion | Nov 12, 2023 – Nov 08, 2024 | Rapid liquidity expansion, broad rally, explosive midcap outperformance (Midcap 150 BM: +37.31%, Next 50 BM: +52.44%). |
| **`year_2`** | Year 2: Valuation Consolidation | Nov 08, 2024 – Nov 07, 2025 | Sharp momentum deceleration; dispersion based on earnings delivery (Next 50 BM: -0.59%, Nifty 50 BM: +5.59%). |
| **`year_3`** | Year 3: Cyclical Correction / Late Cycle | Nov 07, 2025 – Nov 09, 2026 | Subdued macro environment, margin pressure; Nifty 50 benchmark negative (N50 BM: **-1.75%**, Midcap 150 BM: +1.55%). |
| **`first_2y`** | First 2 Years | Nov 12, 2023 – Nov 07, 2025 | Initial 2-Year Compound Expansion Phase (N50: +14.36%, Midcaps: +20.53%). |
| **`trailing_2y`** | Trailing 2 Years | Nov 08, 2024 – Nov 09, 2026 | Post-peak consolidation phase (N50: +1.84%, Next 50: +2.14%, Midcaps: +3.68%). |

---

## 3. Master Multi-Period Realized Performance Matrix

### Table A: Max-Sharpe Optimized Portfolios ($w_i \in [2.5\%, 10.0\%]$, Capital = 100%)

| Time Period | Stock Universe | Target Benchmark CAGR | Applied NIFTY 50 Model | Applied NIFTY NEXT 50 Model | Applied NIFTY MIDCAP 150 Model | Win / Beat Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Full 3-Year Cycle**<br>(Nov 2023 – Nov 2026) | **NIFTY 50** | **8.67%** | **20.62%** *(+11.95% α)* | **22.13%** *(+13.46% α)* | **22.71%** *(+14.04% α)* | **100% Beats BM** |
| | **NIFTY NEXT 50** | **16.62%** | **24.61%** *(+7.98% α)* | **26.07%** *(+9.45% α)* | **26.72%** *(+10.10% α)* | **100% Beats BM** |
| | **NIFTY MIDCAP 150** | **13.79%** | **42.34%** *(+28.55% α)* | **46.58%** *(+32.79% α)* | **46.42%** *(+32.63% α)* | **100% Beats BM** |
| **Year 1: Bull Expansion**<br>(Nov 2023 – Nov 2024) | **NIFTY 50** | **23.91%** | **57.62%** *(+33.71% α)* | **57.86%** *(+33.95% α)* | **60.15%** *(+36.24% α)* | **100% Beats BM** |
| | **NIFTY NEXT 50** | **52.44%** | **58.37%** *(+5.93% α)* | **60.10%** *(+7.66% α)* | **58.97%** *(+6.53% α)* | **100% Beats BM** |
| | **NIFTY MIDCAP 150** | **37.31%** | **110.50%** *(+73.18% α)* | **128.69%** *(+91.38% α)* | **128.79%** *(+91.47% α)* | **100% Beats BM** |
| **Year 2: Consolidation**<br>(Nov 2024 – Nov 2025) | **NIFTY 50** | **5.59%** | **17.41%** *(+11.82% α)* | **19.96%** *(+14.38% α)* | **18.38%** *(+12.79% α)* | **100% Beats BM** |
| | **NIFTY NEXT 50** | **-0.59%** | **12.74%** *(+13.33% α)* | **11.95%** *(+12.54% α)* | **14.79%** *(+15.38% α)* | **100% Beats BM** |
| | **NIFTY MIDCAP 150** | **5.87%** | **22.62%** *(+16.76% α)* | **27.84%** *(+21.98% α)* | **27.44%** *(+21.57% α)* | **100% Beats BM** |
| **Year 3: Cyclical Correction**<br>(Nov 2025 – Nov 2026) | **NIFTY 50** | **-1.75%** | **8.55%** *(+10.30% α)* | **10.58%** *(+12.33% α)* | **9.38%** *(+11.13% α)* | **100% Beats BM** |
| | **NIFTY NEXT 50** | **4.91%** | **23.40%** *(+18.48% α)* | **21.92%** *(+17.00% α)* | **23.58%** *(+18.67% α)* | **100% Beats BM** |
| | **NIFTY MIDCAP 150** | **1.55%** | **24.55%** *(+23.00% α)* | **23.24%** *(+21.69% α)* | **22.21%** *(+20.65% α)* | **100% Beats BM** |
| **First 2 Years**<br>(Nov 2023 – Nov 2025) | **NIFTY 50** | **14.36%** | **28.64%** *(+14.28% α)* | **30.44%** *(+16.08% α)* | **33.00%** *(+18.64% α)* | **100% Beats BM** |
| | **NIFTY NEXT 50** | **23.03%** | **34.14%** *(+11.11% α)* | **33.51%** *(+10.48% α)* | **35.70%** *(+12.67% α)* | **100% Beats BM** |
| | **NIFTY MIDCAP 150** | **20.53%** | **53.55%** *(+33.03% α)* | **65.15%** *(+44.63% α)* | **65.97%** *(+45.45% α)* | **100% Beats BM** |
| **Trailing 2 Years**<br>(Nov 2024 – Nov 2026) | **NIFTY 50** | **1.84%** | **10.83%** *(+8.99% α)* | **12.76%** *(+10.92% α)* | **12.59%** *(+10.75% α)* | **100% Beats BM** |
| | **NIFTY NEXT 50** | **2.14%** | **11.22%** *(+9.08% α)* | **11.60%** *(+9.47% α)* | **13.48%** *(+11.35% α)* | **100% Beats BM** |
| | **NIFTY MIDCAP 150** | **3.68%** | **22.28%** *(+18.60% α)* | **22.98%** *(+19.30% α)* | **22.08%** *(+18.40% α)* | **100% Beats BM** |

---

### Table B: Equal-Weighted 20-Stock Basket Performance (Unbiased, 5% per stock)

| Time Period | NIFTY 50 (BM) | N50 EW | Next 50 EW | Midcap EW | NEXT 50 (BM) | N50 EW | Next 50 EW | Midcap EW | MIDCAP 150 (BM) | N50 EW | Next 50 EW | Midcap EW |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Full 3-Year Cycle** | **8.67%** | 10.92% | 11.95% | 13.10% | **16.62%** | 17.65% | 18.26% | 19.02% | **13.79%** | 27.35% | 29.49% | 29.14% |
| **Year 1 (Bull Rally)** | **23.91%** | 36.64% | 37.37% | 42.55% | **52.44%** | 53.58% | 53.44% | 54.68% | **37.31%** | 80.50% | 92.90% | 94.99% |
| **Year 2 (Consolidation)** | **5.59%** | 4.70% | 5.48% | 5.60% | **-0.59%** | 3.24% | 3.78% | 5.26% | **5.87%** | 10.26% | 12.09% | 11.72% |
| **Year 3 (Correction)** | **-1.75%** | -0.88% | 0.74% | -0.29% | **4.91%** | 7.26% | 7.49% | 7.69% | **1.55%** | 8.94% | 6.20% | 4.13% |
| **First 2 Years** | **14.36%** | 17.82% | 18.56% | 21.00% | **23.03%** | 25.01% | 25.21% | 26.77% | **20.53%** | 38.94% | 44.61% | 45.36% |
| **Trailing 2 Years** | **1.84%** | 1.36% | 2.51% | 2.17% | **2.14%** | 3.73% | 4.57% | 5.21% | **3.68%** | 8.80% | 8.14% | 6.85% |

---

## 4. Empirical Takeaways on Time Transferability

1. **100% Outperformance Across All 54 Combinations in Max-Sharpe Mode:**
   - In every single test case (6 periods $\times$ 3 universes $\times$ 3 models = 54 pairs), the fundamental model beats its target benchmark index.
   - The model features and weights transfer across different market regimes without requiring any parameter tweaking or periodic curve-fitting.
2. **Robust Capital Preservation in Down / Flat Markets:**
   - In **Year 3 (Nov 2025 – Nov 2026)**, when the Nifty 50 benchmark fell **-1.75%**, all three models delivered positive returns (**+8.55% to +10.58%**), generating **over +10% to +12% downside protection alpha**.
   - In **Year 2 (Nov 2024 – Nov 2025)**, when the Nifty Next 50 index declined **-0.59%**, all models generated positive double-digit returns (**+11.95% to +14.79%**).
3. **Midcap Super-Alpha in High-Liquidity Regimes:**
   - In **Year 1 (Bull Expansion)**, high cash-converting midcap compounders surged dramatically: the models generated **110.5% to 128.8% CAGR** versus the benchmark's 37.3% (+73% to +91% active alpha).
4. **Equal-Weighted Basket Resilience:**
   - Even without any Sharpe optimization (pure 5% equal weighting), the fundamental selections beat their benchmark in **51 out of 54 combinations (94.4% win rate)**.

---

## 5. Associated Assets & Verification Protocol

- **Execution Engine:** `research/code/run_multi_period_analysis.py`
- **Unit Test Suite:** `research/code/test_multi_period_transferability.py` (6 automated tests, 100% passing)
- **JSON Dataset:** `research/data/multi_period_transferability_results.json`
- **Full Suite Run:**
  ```bash
  python3 -m unittest discover -s ~/.brain/brain/research/code/ -p "test_*.py"
  # Ran 99 tests in 43.2s — OK (100% passing)
  ```