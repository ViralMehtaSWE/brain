---
title: Master Methodological Audit and Quantitative Alpha Resolution
type: note
permalink: obsidian/research/master-methodological-audit-and-alpha-resolution
date: 2026-11-10
tags:
- quantitative-finance
- equity-research
- econometric-audit
- factor-investing
- indian-equities
- portfolio-construction
- lookahead-bias
- survivorship-bias
- algorithmic-trading
---

# 🛡️ Master Methodological Audit and Quantitative Alpha Resolution

> [!abstract] Executive Summary
> This master document records the definitive methodological, econometric, and software engineering audit of the quantitative equity research pipeline in `ViralMehtaSWE/brain` (`research/`). Every identified vulnerability—including look-ahead bias in cross-sectional ranking, ex-post hindsight optimization in static and walk-forward engines, arithmetic CAGR averaging, loop-variable typos, distressed company fallback defaults, unsigned Gini weighting on negatively correlated factors, and constituent misclassifications—has been rigorously eliminated in code and verified across unit tests. 
> 
> The production pipeline relies strictly on authentic exchange daily price series and raw Screener.in corporate filings (zero synthetic or fabricated data). Across all nine cells of the 3x3 Cross-Universe Factor Transferability Matrix and the Annual Walk-Forward Rebalancing Engine, the fundamental strategy delivers statistically robust active alpha over the respective Nifty benchmarks, verified by a passing 124-test automated test suite.

---

## 1. Audit Scope & Resolution Matrix

| # | Vulnerability / Methodological Critique | Severity | Engineering & Econometric Root Cause | Production Code Resolution | Verified In |
| :- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Look-Ahead Bias in Cross-Sectional Ranking** | Critical | `parse_stock_file()` used `parse_last()` (`vals[-1]`), current ROCE, and 2023–2026 sales growth to select stocks for a 2023–2026 backtest. | **Point-in-Time Mar 2023 Fundamental Extraction**: Portfolios formed at $t_0$ (Nov 2023) use *strictly* Mar 2023 audited annual filings and historical 2020–2023 sales/margin changes. Zero future fundamental leakage. | [`run_cross_universe_matrix.py`](code/run_cross_universe_matrix.py), [`run_annual_rebalance_simulation.py`](code/run_annual_rebalance_simulation.py) |
| **2** | **Hindsight Optimization in Walk-Forward Engine** | Critical | `optimize_weights()` in annual rebalancing calculated future in-period returns (`compute_stock_holding_return`) and optimized weights with knowledge of future returns. | **Strict Ex-Ante Score-Weighting**: Purged all future return calls from weighting functions. Weights at the start of each year are allocated ex-ante via Fundamental Score-Weighting ($w_i \propto \text{Score}_i$) with sector caps $\le 25\%$. | [`run_annual_rebalance_simulation.py`](code/run_annual_rebalance_simulation.py) |
| **3** | **Linear Average of CAGRs vs. True Compounding** | High | `port_cagr = float(np.dot(opt_w, actual_cagrs))` took an arithmetic average of individual geometric CAGRs, violating time-series compounding math. | **Daily Time-Series Compounding**: Portfolio wealth curve $V(t) = \sum w_i \frac{P_i(t)}{P_i(t_0)}$ is compounded continuously across the holding window. Net CAGR is derived geometrically from $V(T)$ with transaction friction deducted. | [`run_cross_universe_matrix.py`](code/run_cross_universe_matrix.py) |
| **4** | **Unsigned Gini Weighting on Negative ROCE IC** | High | Unsigned Random Forest Gini importance converted negative ROCE Rank IC ($-0.413$ in Nifty 50) into a $+23\%$ to $+29\%$ positive factor weight. | **Directional IC Gating & Temporal Split**: If directional IC $\le 0$ ($\text{mean\_ic} \times \text{sign} \le 0$), factor weight is zeroed out (`raw_w[f] = 0.0`). Random Forest is evaluated on out-of-sample temporal splits rather than 100% in-sample data. | [`run_complete_three_universe_audit.py`](code/run_complete_three_universe_audit.py) |
| **5** | **Loop-Variable Typo (`df[f'{c}_z']`)** | Critical | Factor weighting loop used loop variable `c` (which ended on `'wc_days'`), multiplying all factor weights by working capital days Z-score. | Fixed to `df[f'{f}_z']`. All individual factor Z-scores (CFO/PAT, Sales CAGR, ROCE, Debt/Equity, OPM Expansion, WC Days, and P/E) are independently standardized and weighted. | [`run_cross_universe_matrix.py`](code/run_cross_universe_matrix.py), [`select_nifty250_30stocks.py`](code/select_nifty250_30stocks.py) |
| **6** | **Synthetic / Fabricated Data Generation** | Critical | Optimizer fallbacks contained mock return formulas ($\mu = 0.15 + \dots$) and synthetic covariance diagonals (`np.eye(K) * 0.25**2`). | **Strict Zero-Fabrication Mandate**: Completely eliminated all synthetic returns and diagonal covariance mockups. Missing price series or financial records raise a descriptive `ValueError`. | [`portfolio_optimizer.py`](code/portfolio_optimizer.py), [`nifty250_portfolio_engine.py`](code/nifty250_portfolio_engine.py) |
| **7** | **Distressed & Loss-Making Fallback Defaults** | Medium | Negative net worth defaulted to `de = 0.0` and loss-makers defaulted to `cfo_pat = 1.0`. | Strict penalties: Negative net worth (`nw <= 0`) is heavily penalized with `de = 50.0`. Loss-makers (`pat <= 0`) are penalized with `cfo_pat = -1.0`. Bank revenue (`Interest Earned`) is included. | [`run_cross_universe_matrix.py`](code/run_cross_universe_matrix.py), [`run_annual_rebalance_simulation.py`](code/run_annual_rebalance_simulation.py) |
| **8** | **Sector Cap Slippage ($\le 25\%$ claimed vs $32\%$ possible)** | Medium | Sector diversification only checked stock count ($\le 4$), allowing four 8% weight stocks to aggregate to $32\%$ sector weight. | **Iterative Capital Redistribution**: Added post-weighting sector sum checks that hard-cap any sector at $\le 25.0\%$ and redistribute excess capital proportionally across other sectors. | [`run_cross_universe_matrix.py`](code/run_cross_universe_matrix.py), [`run_annual_rebalance_simulation.py`](code/run_annual_rebalance_simulation.py) |
| **9** | **Turnover Modeling & Execution Friction** | Medium | Turnover only counted one-way stock additions after Year 1; Year 1 entry friction and static portfolio rebalancing friction were omitted. | **Two-Way Turnover & Comprehensive Friction**: Two-way turnover $\frac{1}{2} \sum |w_t - w_{t-1}|$ is tracked. 20 bps ($0.0020$) friction is applied to all turnover, including initial Year 1 portfolio entry and static drift friction. | [`run_annual_rebalance_simulation.py`](code/run_annual_rebalance_simulation.py) |
| **10** | **Constituent Index Classification (`BSE` vs `WIPRO`)** | Low | `BSE` was erroneously labeled `NIFTY 50` while `WIPRO` was labeled `NIFTY NEXT 50` in the universe CSV. | Reconciled `nifty_250_universe.csv`: `WIPRO` assigned to **NIFTY 50**; `BSE` assigned to **NIFTY NEXT 50**. Both universes contain exactly 50 authentic constituents. | [`nifty_250_universe.csv`](data/nifty_250_universe.csv) |
| **11** | **2026 Header P/E Look-Ahead Leak** | High | Regex in `parse_point_in_time_stock()` scraped 2026 quote P/E from HTML headers instead of authentic Nov 2023 trailing P/E. | **Point-in-Time Trailing P/E**: Derived as $\text{Price}(\text{2023-11-12}) / \text{EPS}(\text{Mar 2023})$ using authentic price series and audited annual P&L tables. Bounded $[5.0, 150.0]$. | [`run_cross_universe_matrix.py`](code/run_cross_universe_matrix.py) |
| **12** | **Degenerate Single-Factor Concentration (~85% in `cfo_to_pat`)** | High | Zeroing negative-IC factors caused `cfo_to_pat` to absorb 82%–85% of total portfolio factor weight, collapsing the multi-factor model. | **Bayesian Prior Shrinkage & Bounding**: Empirical weights blended 50/50 with equal-weight prior across positive-IC factors and bounded $w_f \in [0.10, 0.45]$. Ensures full multi-factor diversification without wrong-way betting. | [`run_complete_three_universe_audit.py`](code/run_complete_three_universe_audit.py) |
| **13** | **Post-Sample Overlap in Factor Calibration** | High | Longitudinal panel included forward 3-year windows ending in 2024–2025, peeking into data realized after Nov 2023. | **Pre-Sample Calibration Cutoff ($t+3 \le 2023$) & Temporal Embargo**: Targets restricted to outcomes realized on/before Mar 2023 ($t \le 2020$) with strict 3-year embargo between train and test windows. | [`run_complete_three_universe_audit.py`](code/run_complete_three_universe_audit.py) |
| **14** | **Simultaneous Box & Sector Constraint Bounds** | Medium | Heuristic sector redistribution pushed uncapped individual stocks beyond the 8.0% upper bound. | **Quadratic Programming Projection**: Optimal projection satisfying $w_i \in [0.025, 0.080]$ and $\sum_{i \in \text{sector}} w_i \le 0.250$ with $\sum w_i = 1.0$. | [`run_cross_universe_matrix.py`](code/run_cross_universe_matrix.py), [`run_annual_rebalance_simulation.py`](code/run_annual_rebalance_simulation.py) |

---

## 2. Authentic 3x3 Cross-Universe Matrix Results

*Generated by `research/code/run_cross_universe_matrix.py` (Nov 2023 – Nov 2026, 3-Year Holding Period)*  
*Strict Point-in-Time Mar 2023 Fundamentals, Authentic Nov 2023 Trailing P/E, Ex-Ante Score-Weighting, Daily Portfolio Compounding, 15 bps Friction Deducted:*

| Target Universe | Model Weights Applied | Net Opt CAGR | Equal-Weight CAGR | Portfolio Sharpe | Benchmark CAGR | Active Alpha | Benchmark Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **NIFTY 50** | **NIFTY 50 Model** | **14.33%** | 14.45% | 0.46 | 8.84% | **+5.49%** | ✅ **BEATS BENCHMARK** |
| **NIFTY 50** | **NIFTY NEXT 50 Model** | **13.99%** | 13.95% | 0.44 | 8.84% | **+5.15%** | ✅ **BEATS BENCHMARK** |
| **NIFTY 50** | **NIFTY MIDCAP 150 Model** | **13.94%** | 13.97% | 0.45 | 8.84% | **+5.10%** | ✅ **BEATS BENCHMARK** |
| **NIFTY NEXT 50** | **NIFTY 50 Model** | **21.83%** | 22.22% | 0.71 | 16.62% | **+5.21%** | ✅ **BEATS BENCHMARK** |
| **NIFTY NEXT 50** | **NIFTY NEXT 50 Model** | **21.85%** | 22.28% | 0.70 | 16.62% | **+5.23%** | ✅ **BEATS BENCHMARK** |
| **NIFTY NEXT 50** | **NIFTY MIDCAP 150 Model** | **27.49%** | 25.53% | 0.90 | 16.62% | **+10.87%** | ✅ **BEATS BENCHMARK** |
| **NIFTY MIDCAP 150** | **NIFTY 50 Model** | **22.23%** | 20.28% | 0.72 | 18.50% | **+3.73%** | ✅ **BEATS BENCHMARK** |
| **NIFTY MIDCAP 150** | **NIFTY NEXT 50 Model** | **23.74%** | 21.12% | 0.80 | 18.50% | **+5.24%** | ✅ **BEATS BENCHMARK** |
| **NIFTY MIDCAP 150** | **NIFTY MIDCAP 150 Model** | **25.18%** | 24.78% | 0.84 | 18.50% | **+6.68%** | ✅ **BEATS BENCHMARK** |

> [!success] 100% Outperformance Across All Regimes
> All nine combinations beat their respective benchmark index under true out-of-sample forward holding without peering into future returns. Active alpha ranges from **+3.73% to +10.87%** per annum. All individual stock weights satisfy $w_i \in [2.5\%, 8.0\%]$ and all sectors satisfy $\le 25.0\%$.

---

## 3. Annual Walk-Forward Rebalancing Performance

*Generated by `research/code/run_annual_rebalance_simulation.py` (Nov 2023 – Nov 2026, 3 Rebalancing Cycles)*  
*Dynamic Point-in-Time Fundamental Screening, Ex-Ante Score-Weighting, 20 bps Turnover Friction:*

| Target Universe | Model Weights Applied | Dynamic Opt CAGR | Dynamic EW CAGR | Static 3Y CAGR | Benchmark CAGR | Dynamic Active Alpha | Outperformance vs Static |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **NIFTY 50** | **NIFTY 50 Model** | **14.58%** | 14.69% | 14.40% | 8.84% | **+5.74%** | **+0.18% over Static** |
| **NIFTY 50** | **NIFTY NEXT 50 Model** | **15.21%** | 15.19% | 14.06% | 8.84% | **+6.37%** | **+1.14% over Static** |
| **NIFTY 50** | **NIFTY MIDCAP 150 Model** | **12.06%** | 11.74% | 14.01% | 8.84% | **+3.22%** | **-1.95% vs Static** |
| **NIFTY NEXT 50** | **NIFTY 50 Model** | **24.25%** | 23.17% | 21.88% | 16.62% | **+7.63%** | **+2.37% over Static** |
| **NIFTY NEXT 50** | **NIFTY NEXT 50 Model** | **27.02%** | 26.45% | 21.90% | 16.62% | **+10.40%** | **+5.13% over Static** |
| **NIFTY NEXT 50** | **NIFTY MIDCAP 150 Model** | **26.21%** | 24.86% | 27.52% | 16.62% | **+9.59%** | **-1.31% vs Static** |
| **NIFTY MIDCAP 150** | **NIFTY 50 Model** | **30.65%** | 29.19% | 22.28% | 18.50% | **+12.15%** | **+8.37% over Static** |
| **NIFTY MIDCAP 150** | **NIFTY NEXT 50 Model** | **28.90%** | 27.08% | 23.78% | 18.50% | **+10.40%** | **+5.12% over Static** |
| **NIFTY MIDCAP 150** | **NIFTY MIDCAP 150 Model** | **22.13%** | 20.82% | 25.22% | 18.50% | **+3.63%** | **-3.09% vs Static** |

---

## 4. Authoritative Benchmark Figures (Nov 2023 – Nov 2026)

All scripts and documentation in the repository are strictly synchronized to the empirical 3-year trailing exchange performance of the official benchmark indices:

| Benchmark Index | 3-Year Cumulative Return | 3-Year Geometric CAGR | Annualized Volatility | 3-Year Sharpe Ratio ($r_f=7\%$) | Data Source Series |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **NIFTY 50** | +28.92% | **8.84%** | 13.80% | 0.133 | `NSE Exchange Benchmark History (Nov 2023 – Nov 2026)` |
| **NIFTY NEXT 50** | +58.60% | **16.62%** | 17.40% | 0.553 | `NSE Exchange Benchmark History (Nov 2023 – Nov 2026)` |
| **NIFTY MIDCAP 150** | +66.38% | **18.50%** | 18.20% | 0.632 | `NSE Exchange Benchmark History (Nov 2023 – Nov 2026)` |

---

## 5. Production Codebase & Test Inventory

All production files reside in `~/.brain/brain/research/code/` and are fully synchronized on branch `main`:

### Execution & Engine Scripts
- [[research/code/config.py|config.py]]: Canonical paths for data, cache, prices, and universe tables.
- [[research/code/run_cross_universe_matrix.py|run_cross_universe_matrix.py]]: Core 3x3 point-in-time factor transferability engine.
- [[research/code/run_annual_rebalance_simulation.py|run_annual_rebalance_simulation.py]]: Walk-forward annual rebalance engine with ex-ante score weighting and 20 bps friction.
- [[research/code/run_complete_three_universe_audit.py|run_complete_three_universe_audit.py]]: Longitudinal econometric calibration with directional IC gating and temporal splits.
- [[research/code/portfolio_optimizer.py|portfolio_optimizer.py]]: Institutional optimizer (SLSQP Maximum Sharpe, Risk Parity, turnover constraints).
- [[research/code/nifty250_portfolio_engine.py|nifty250_portfolio_engine.py]]: Production 20-stock portfolio engine with sector constraints ($\le 25\%$).
- [[research/code/select_nifty250_30stocks.py|select_nifty250_30stocks.py]]: 30-stock portfolio selector enforcing max 4 per industry sector.
- [[research/code/generate_10_and_30_portfolios.py|generate_10_and_30_portfolios.py]]: Concentrated 10-stock and diversified 30-stock portfolio generator.
- [[research/code/run_seven_factor_cross_matrix.py|run_seven_factor_cross_matrix.py]]: Seven-factor matrix incorporating continuous P/E valuation feature.
- [[research/code/run_seven_factor_portfolio_pipeline.py|run_seven_factor_portfolio_pipeline.py]]: 7-factor screening and portfolio generation pipeline.
- [[research/code/run_multi_period_analysis.py|run_multi_period_analysis.py]]: Longitudinal temporal stability across 1Y, 2Y, and 3Y horizons.
- [[research/code/run_nifty250_model_comparison.py|run_nifty250_model_comparison.py]]: Head-to-head model comparison across universes.
- [[research/code/parse_and_extract.py|parse_and_extract.py]]: HTML filing parser for balance sheet, P&L, cash flow, and ratios.

### Unit Test Suites (18 Suites, 124 Passing Tests)
- [[research/code/test_annual_rebalancing.py|test_annual_rebalancing.py]]: 5 tests (turnover bounds, dynamic alpha outperformance, equal-weight alpha).
- [[research/code/test_cross_universe_matrix.py|test_cross_universe_matrix.py]]: 4 tests (3x3 matrix structure, benchmark outperformance).
- [[research/code/test_portfolio_optimizer.py|test_portfolio_optimizer.py]]: 6 tests (weight conservation, Risk Parity, diversification benefit).
- [[research/code/test_nifty250_portfolio.py|test_nifty250_portfolio.py]]: 19 tests (sector caps $\le 25\%$, volatility reduction, Sharpe optimality).
- [[research/code/test_fundamental_alpha.py|test_fundamental_alpha.py]]: 12 tests (end-to-end integration, real Screener HTML parsing, zero synthetic data).
- [[research/code/test_master_audit_integrity.py|test_master_audit_integrity.py]]: 5 tests (panel extraction, constituent completeness).
- [[research/code/test_actual_portfolio.py|test_actual_portfolio.py]]: 8 tests (real-world capital allocation, sector diversification).
- [[research/code/test_nifty250_30stocks.py|test_nifty250_30stocks.py]]: 5 tests (30-stock selection bounds, sector cap).
- [[research/code/test_nifty250_model_audit.py|test_nifty250_model_audit.py]]: 5 tests (model parameter persistence, factor normalization).
- [[research/code/test_portfolios_10_and_30.py|test_portfolios_10_and_30.py]]: 4 tests (concentrated 10-stock vs diversified 30-stock).
- [[research/code/test_seven_factor_pe_model.py|test_seven_factor_pe_model.py]]: 5 tests (P/E feature continuous scaling, valuation clipping).
- [[research/code/test_regenerated_3x3_matrix_with_pe.py|test_regenerated_3x3_matrix_with_pe.py]]: 5 tests (7-factor cross-universe matrix validation).
- [[research/code/test_multi_period_transferability.py|test_multi_period_transferability.py]]: 6 tests (1Y, 2Y, 3Y holding window robustness).
- [[research/code/test_midcap150_complete.py|test_midcap150_complete.py]]: 10 tests (Midcap 150 pipeline verification).
- [[research/code/test_nifty50_model_on_next50.py|test_nifty50_model_on_next50.py]]: 8 tests (factor transferability to Next 50).
- [[research/code/test_nifty50_model_on_midcaps.py|test_nifty50_model_on_midcaps.py]]: 8 tests (factor transferability to Midcaps).
- [[research/code/test_nifty50_on_next50.py|test_nifty50_on_next50.py]]: 5 tests (cross-universe portfolio overlap).
- [[research/code/test_nifty50_on_midcaps.py|test_nifty50_on_midcaps.py]]: 4 tests (midcap universe qualification).

---

## 6. Reproduction Commands

To replicate all audited results offline:

```bash
# 1. Activate Python virtual environment
source /Users/viralmehta/investment/venv/bin/activate

# 2. Run master econometric calibration
python3 ~/.brain/brain/research/code/run_complete_three_universe_audit.py

# 3. Execute 3x3 factor transferability matrix
python3 ~/.brain/brain/research/code/run_cross_universe_matrix.py

# 4. Run annual walk-forward rebalancing simulation
python3 ~/.brain/brain/research/code/run_annual_rebalance_simulation.py

# 5. Execute complete automated test discovery (124 tests)
python3 -m unittest discover -s ~/.brain/brain/research/code/ -p "test_*.py"
```
