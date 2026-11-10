---
title: Annual Walk-Forward Rebalancing of Fundamental Portfolios
type: note
permalink: obsidian/research/annual-walk-forward-rebalancing-of-fundamental-portfolios
tags:
- quantitative-finance
- portfolio-rebalancing
- annual-rebalancing
- turnover
- walk-forward
- indian-equities
---

# 🔄 Annual Walk-Forward Rebalancing of Fundamental Portfolios

## 1. Rebalancing Framework & Execution Rules

When managing real-world systematic portfolios, portfolios are **rebalanced on a periodic schedule (once a year)** rather than held static indefinitely:
- **Rebalance Frequency:** Exactly once every 12 months (each November, following the release and filing of full-year audited annual financial statements).
- **Point-in-Time Accounting Data:**
  - **Year 1 (Nov 12, 2023 – Nov 08, 2024):** Constructed using **FY2023** audited financials.
  - **Year 2 (Nov 08, 2024 – Nov 07, 2025):** Rebalanced using **FY2024** audited financials.
  - **Year 3 (Nov 07, 2025 – Nov 09, 2026):** Rebalanced using **FY2025** audited financials.
- **Model Features & Weights (100% Frozen):**
  - Scoring models, formulas, and factor weights are held strictly unchanged across all years.
- **Transaction Drag / Execution Friction:**
  - Subtracted realistic round-trip brokerage, STT, exchange fees, and bid-ask slippage of **0.15% per unit of portfolio turnover**.
- **Portfolio Constraints (Strictly Enforced):**
  - Exactly 20 stocks per basket.
  - Position limits: $2.5\% \le w_i \le 10.0\%$.
  - Capital conservation: $\sum w_i \equiv 100.0\%$.
  - Sector diversification: maximum 4 stocks per industry.

---

## 2. Dynamic Annual Rebalancing vs. Benchmark Results

### Table A: 3-Year Compounded Outcomes Under Annual Rebalancing

| Stock Universe | Benchmark 3Y Cumulative | Benchmark Annualized CAGR | Applied Model | Dynamic Rebalanced Cum Return | Dynamic Rebalanced CAGR | Active Alpha ($\alpha$) | Dynamic Annual Path [Y1, Y2, Y3] | Avg Annual Turnover |
| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **NIFTY 50** | **+28.27%** | **8.68%** | **NIFTY 50 Model** | **+105.80%** | **27.27%** | <span style="color:green">**+18.59%**</span> | [+53.08%, +22.14%, +9.99%] | 27.5% |
| | | | **NIFTY NEXT 50 Model** | **+110.87%** | **28.19%** | <span style="color:green">**+19.51%**</span> | [+52.50%, +23.88%, +11.22%] | 30.0% |
| | | | **NIFTY MIDCAP 150 Model** | **+100.75%** | **26.35%** | <span style="color:green">**+17.66%**</span> | [+44.53%, +24.45%, +11.87%] | 30.0% |
| **NIFTY NEXT 50** | **+58.43%** | **16.64%** | **NIFTY 50 Model** | **+121.05%** | **29.96%** | <span style="color:green">**+13.32%**</span> | [+56.42%, +15.25%, +21.44%] | 25.0% |
| | | | **NIFTY NEXT 50 Model** | **+123.83%** | **30.41%** | <span style="color:green">**+13.77%**</span> | [+55.38%, +15.95%, +22.77%] | 27.5% |
| | | | **NIFTY MIDCAP 150 Model** | **+146.59%** | **33.97%** | <span style="color:green">**+17.34%**</span> | [+59.84%, +19.77%, +25.25%] | 27.5% |
| **NIFTY MIDCAP 150** | **+47.19%** | **13.80%** | **NIFTY 50 Model** | **+192.14%** | **40.63%** | <span style="color:green">**+26.83%**</span> | [+79.01%, +20.57%, +28.42%] | 30.0% |
| | | | **NIFTY NEXT 50 Model** | **+191.54%** | **40.55%** | <span style="color:green">**+26.75%**</span> | [+65.89%, +30.02%, +28.28%] | 40.0% |
| | | | **NIFTY MIDCAP 150 Model** | **+195.34%** | **41.04%** | <span style="color:green">**+27.24%**</span> | [+66.67%, +30.21%, +28.84%] | 40.0% |

---

## 3. Dynamic Rebalancing vs. Static Buy-and-Hold Comparison

Does updating constituent holdings every year using the latest corporate filings add value over buying once and holding for 3 years?

| Universe | Model | Static 3Y Holding CAGR | Dynamic Annual Rebalancing CAGR | Rebalancing Value Add ($\Delta$) | Rebalancing Benefit |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **NIFTY 50** | NIFTY 50 Model | 22.81% | **27.27%** | <span style="color:green">**+4.46% CAGR**</span> | Replaces deteriorating cash converters |
| | NIFTY NEXT 50 Model | 23.82% | **28.19%** | <span style="color:green">**+4.37% CAGR**</span> | Captures emerging compounders |
| | NIFTY MIDCAP 150 Model | 19.71% | **26.35%** | <span style="color:green">**+6.64% CAGR**</span> | Rotates out of margin-compressed names |
| **NIFTY NEXT 50** | NIFTY 50 Model | 28.52% | **29.96%** | <span style="color:green">**+1.44% CAGR**</span> | Trims cyclical large-mid laggards |
| | NIFTY NEXT 50 Model | 28.90% | **30.41%** | <span style="color:green">**+1.51% CAGR**</span> | Reinvests into top sales growers |
| | NIFTY MIDCAP 150 Model | 30.21% | **33.97%** | <span style="color:green">**+3.76% CAGR**</span> | High operating leverage rotation |
| **NIFTY MIDCAP 150**| NIFTY 50 Model | 35.95% | **40.63%** | <span style="color:green">**+4.68% CAGR**</span> | Avoids midcap balance-sheet decay |
| | NIFTY NEXT 50 Model | 34.06% | **40.55%** | <span style="color:green">**+6.49% CAGR**</span> | Exploits midcap growth breakouts |
| | NIFTY MIDCAP 150 Model | 33.35% | **41.04%** | <span style="color:green">**+7.69% CAGR**</span> | Native midcap margin expansion capture |

---

## 4. Key Empirical Takeaways

1. **Rebalancing Generates +1.4% to +7.7% Annualized Excess Alpha:**  
   In all 9 cross-universe combinations, dynamic annual rebalancing outperforms a static 3-year holding strategy, even after deducting realistic transaction costs (0.15% drag per turnover).
2. **Moderate & Manageable Turnover (25% to 40%):**  
   On average, 5 to 8 stocks out of 20 are rotated each November. The core franchise compounders (high ROCE + high CFO/PAT franchises like `MCX`, `GVT&D`, `BSE`, `HINDCOPPER`) remain in the portfolio continuously, while cyclical laggards with deteriorating working capital or declining margins are disciplined out.
3. **Robustness in Down Years (Year 3):**  
   In Year 3 (Nov 2025 – Nov 2026), when the Nifty 50 benchmark fell **-1.76%**, the rebalanced portfolio generated **+9.99% to +11.87%** return in Nifty 50, and **+28.42% to +28.84%** in Midcap 150, because the Year 2 rebalance had rotated out of companies whose operating margins compressed.

---

## 5. Code & Verification Assets

- **Simulation Engine:** `research/code/run_annual_rebalance_simulation.py`
- **Unit Test Suite:** `research/code/test_annual_rebalancing.py` (5 automated tests)
- **JSON Dataset:** `research/data/annual_rebalance_results.json`
- **Full Suite Run:**
  ```bash
  python3 -m unittest discover -s ~/.brain/brain/research/code/ -p "test_*.py"
  Ran 104 tests in 47.25s — OK (100% passing across 11 test files)
  ```