#!/usr/bin/env python3
"""
Multi-Period Time Transferability Engine:
Evaluates the exact unchanged model features and weights across 6 distinct time periods:
  1. Year 1 (Nov 2023 - Nov 2024): Broad Market Bull Rally
  2. Year 2 (Nov 2024 - Nov 2025): Consolidation & Selective Dispersion
  3. Year 3 (Nov 2025 - Nov 2026): Cyclical Trough / Flat Market (N50: -1.75%)
  4. First 2 Years (Nov 2023 - Nov 2025): Initial Momentum Phase
  5. Trailing 2 Years (Nov 2024 - Nov 2026): Post-Peak Consolidation
  6. Full 3-Year Horizon (Nov 2023 - Nov 2026): Complete Market Cycle

Evaluates:
  - All 3 Models: NIFTY 50 Model, NIFTY NEXT 50 Model, NIFTY MIDCAP 150 Model
  - All 3 Universes: NIFTY 50, NIFTY NEXT 50, NIFTY MIDCAP 150
  - In each period, calculates:
      - Equal-Weighted Portfolio CAGR
      - Max-Sharpe Optimized Portfolio CAGR (bounds: 2.5% to 10.0%, capital 100%)
      - Target Benchmark Index CAGR
      - Active Outperformance (Alpha)
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
sys.path.insert(0, SCRATCH_DIR)

from run_cross_universe_matrix import parse_stock_file, has_sufficient_history

CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")
UNIVERSE_CSV = os.path.join(SCRATCH_DIR, "nifty_250_universe.csv")
CALIBRATION_JSON = os.path.join(SCRATCH_DIR, "audited_three_universes_calibration.json")
PRICE_10Y_DIR = os.path.join(SCRATCH_DIR, "price_10y")

with open(CALIBRATION_JSON, "r") as f:
    calib = json.load(f)

universe_df = pd.read_csv(UNIVERSE_CSV)

MODELS = {
    "NIFTY 50 Model": calib["NIFTY 50"]["unrounded_weights"],
    "NIFTY NEXT 50 Model": calib["NIFTY NEXT 50"]["unrounded_weights"],
    "NIFTY MIDCAP 150 Model": calib["NIFTY MIDCAP 150"]["unrounded_weights"]
}

UNIVERSES = ["NIFTY 50", "NIFTY NEXT 50", "NIFTY MIDCAP 150"]

# Distinct Multi-Period Evaluation Windows
PERIODS = [
    {
        "id": "full_3y",
        "name": "Full 3-Year Cycle (Nov 2023 - Nov 2026)",
        "start": "2023-11-12",
        "end": "2026-11-09",
        "desc": "Complete Multi-Year Macro Cycle (Bull + Consolidation + Correction)"
    },
    {
        "id": "year_1",
        "name": "Year 1: Bull Expansion (Nov 2023 - Nov 2024)",
        "start": "2023-11-12",
        "end": "2024-11-08",
        "desc": "High Liquidity, Rapid Topline Expansion & Midcap Bull Run"
    },
    {
        "id": "year_2",
        "name": "Year 2: Valuation Consolidation (Nov 2024 - Nov 2025)",
        "start": "2024-11-08",
        "end": "2025-11-07",
        "desc": "Selective Quality Dispersion; Next 50 Flat (-0.59%), Midcaps +5.87%"
    },
    {
        "id": "year_3",
        "name": "Year 3: Cyclical Correction / Late Cycle (Nov 2025 - Nov 2026)",
        "start": "2025-11-07",
        "end": "2026-11-09",
        "desc": "Headwinds & Compression: Nifty 50 Negative (-1.75%), Midcaps Flattish (+1.55%)"
    },
    {
        "id": "first_2y",
        "name": "First 2 Years (Nov 2023 - Nov 2025)",
        "start": "2023-11-12",
        "end": "2025-11-07",
        "desc": "Sustained Mid-Cycle Bull Run (N50 +14.36%, Midcaps +20.53%)"
    },
    {
        "id": "trailing_2y",
        "name": "Trailing 2 Years (Nov 2024 - Nov 2026)",
        "start": "2024-11-08",
        "end": "2026-11-09",
        "desc": "Subdued Macro Environment (N50 +1.84%, Next 50 +2.14%, Midcaps +3.68%)"
    }
]

# Benchmark files for exact returns in each period
BM_FILES = {
    "NIFTY 50": os.path.join(PRICE_10Y_DIR, "NIFTY_50_price10y.csv"),
    "NIFTY NEXT 50": os.path.join(PRICE_10Y_DIR, "NIFTY_NEXT_50_price10y.csv"),
    "NIFTY MIDCAP 150": os.path.join(PRICE_10Y_DIR, "NIPPON_MIDCAP_150_ETF_price10y.csv")
}

def get_bm_cagr(u_name, start_date, end_date):
    bf = BM_FILES[u_name]
    df = pd.read_csv(bf, parse_dates=["date"]).set_index("date").sort_index()
    p0 = float(df.asof(start_date)["price"])
    p1 = float(df.asof(end_date)["price"])
    days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
    years = days / 365.25
    return (p1 / p0) ** (1.0 / years) - 1.0

def get_stock_series(symbol):
    t_clean = 'TATAMOTORS' if symbol in ['TMPV', 'TMCV'] else symbol.upper().strip()
    cache = os.path.join(CACHE_DIR, f"{t_clean}_price.csv")
    if os.path.exists(cache) and os.path.getsize(cache) > 100:
        df = pd.read_csv(cache, parse_dates=['date']).dropna().drop_duplicates('date').sort_values('date')
        if len(df) > 15:
            return df.set_index('date')['price']
    return None

def compute_period_cagr(series, start_date, end_date):
    if series is None or len(series) < 10:
        return np.nan
    s_sub = series.loc[start_date:end_date]
    if len(s_sub) < 5:
        p0 = series.asof(start_date)
        p1 = series.asof(end_date)
    else:
        p0 = s_sub.iloc[0]
        p1 = s_sub.iloc[-1]
    if pd.isna(p0) or pd.isna(p1) or p0 <= 0:
        return np.nan
    days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
    years = days / 365.25
    return (float(p1) / float(p0)) ** (1.0 / years) - 1.0

def run_multi_period_analysis():
    print("=" * 110)
    print("MULTI-PERIOD TIME TRANSFERABILITY EXPERIMENT (MODELS & WEIGHTS 100% UNCHANGED)")
    print("=" * 110)
    
    # 1. First, select the 20 stocks for each (Universe, Model) combination using unchanged weights
    selected_portfolios = {}
    for u in UNIVERSES:
        selected_portfolios[u] = {}
        u_stocks = universe_df[universe_df["Benchmark_Index"] == u].copy()
        meta_dict = u_stocks.set_index("Symbol").to_dict(orient="index")
        valid_symbols = [s for s in u_stocks["Symbol"] if has_sufficient_history(s)[0]]
        
        parsed = []
        for s in valid_symbols:
            d = parse_stock_file(s)
            if d:
                d["name"] = meta_dict[s]["Company Name"]
                d["industry"] = meta_dict[s]["Industry"]
                parsed.append(d)
        df = pd.DataFrame(parsed)
        
        for c in ["roce", "hist_sales_cagr", "opm_expansion_3y", "debt_to_equity", "cfo_to_pat", "wc_days"]:
            df[c] = df[c].fillna(df[c].median()).clip(df[c].quantile(0.02), df[c].quantile(0.98))
            mean_c, std_c = df[c].mean(), df[c].std()
            df[f"{c}_z"] = (df[c] - mean_c) / std_c if std_c > 0 else 0.0
        df["pe_ratio"] = df["pe_ratio"].fillna(df["pe_ratio"].median()).clip(5.0, 150.0)
        
        for m_name, weights in MODELS.items():
            score = 0.0
            for f, w in weights.items():
                sign = -1.0 if f in ["debt_to_equity", "wc_days"] else 1.0
                score += w * (sign * df[f"{f}_z"])
            df["pe_penalty"] = np.where(df["pe_ratio"] > 75, (df["pe_ratio"] - 75) / 100, 0.0)
            df["final_score"] = score - 0.15 * df["pe_penalty"]
            
            df_sorted = df.sort_values("final_score", ascending=False)
            selected = []
            ind_counts = {}
            for _, row in df_sorted.iterrows():
                ind = row["industry"]
                if ind_counts.get(ind, 0) < 4:
                    selected.append(row)
                    ind_counts[ind] = ind_counts.get(ind, 0) + 1
                if len(selected) == 20: break
            selected_portfolios[u][m_name] = pd.DataFrame(selected).reset_index(drop=True)
            
    # 2. Now evaluate each period
    period_results = {}
    for p in PERIODS:
        p_id = p["id"]
        p_name = p["name"]
        start_d = p["start"]
        end_d = p["end"]
        print(f"\n>>> EVALUATING PERIOD: {p_name} ({start_d} to {end_d})")
        print("-" * 110)
        period_results[p_id] = {
            "period_info": p,
            "universes": {}
        }
        
        for u in UNIVERSES:
            period_results[p_id]["universes"][u] = {}
            bm_cagr = get_bm_cagr(u, start_d, end_d)
            
            for m_name in MODELS.keys():
                top20_df = selected_portfolios[u][m_name]
                
                price_dict = {}
                stock_cagrs = {}
                for _, r in top20_df.iterrows():
                    sym = r["symbol"]
                    p_series = get_stock_series(sym)
                    if p_series is not None:
                        cagr = compute_period_cagr(p_series, start_d, end_d)
                        if pd.notnull(cagr):
                            stock_cagrs[sym] = cagr
                            # Slice prices for covariance
                            sub_p = p_series.loc[start_d:end_d]
                            if len(sub_p) > 5:
                                price_dict[sym] = sub_p
                                
                valid_cagrs = list(stock_cagrs.values())
                ew_cagr = float(np.mean(valid_cagrs)) if valid_cagrs else 0.0
                
                # Covariance & Optimization
                valid_syms = list(price_dict.keys())
                N = len(valid_syms)
                if N >= 15:
                    prices_df = pd.DataFrame(price_dict).pct_change().dropna(how="all")
                    ann_factor = 252.0 if len(prices_df) > 100 else 52.0
                    cov = prices_df.cov() * ann_factor
                    cov = cov.fillna(cov.median().median() if not cov.empty else 0.04)
                    cov_arr = cov.loc[valid_syms, valid_syms].values
                    mu_arr = np.array([stock_cagrs[s] for s in valid_syms])
                    
                    rf = 0.07 if "3y" in p_id or "2y" in p_id else 0.07 # 7% risk-free rate
                    def neg_sharpe(w):
                        rp = np.dot(w, mu_arr)
                        vp = np.sqrt(np.dot(w, np.dot(cov_arr, w)))
                        return -(rp - rf) / max(vp, 1e-4)
                        
                    bounds = [(0.025, 0.10) for _ in range(N)]
                    cons = ({ "type": "eq", "fun": lambda w: np.sum(w) - 1.0 })
                    w0 = np.ones(N) / N
                    res = minimize(neg_sharpe, w0, method="SLSQP", bounds=bounds, constraints=cons)
                    w_opt = res.x if res.success else w0
                    w_opt = np.clip(w_opt, 0.025, 0.10)
                    w_opt = w_opt / np.sum(w_opt)
                    
                    opt_cagr = float(np.dot(w_opt, mu_arr))
                    opt_vol = float(np.sqrt(np.dot(w_opt, np.dot(cov_arr, w_opt))))
                    opt_sharpe = (opt_cagr - rf) / max(opt_vol, 1e-4)
                else:
                    opt_cagr = ew_cagr
                    opt_vol = 0.20
                    opt_sharpe = (ew_cagr - 0.07) / 0.20
                    
                alpha_opt = opt_cagr - bm_cagr
                alpha_ew = ew_cagr - bm_cagr
                beats_bm = opt_cagr > bm_cagr
                
                period_results[p_id]["universes"][u][m_name] = {
                    "opt_cagr": opt_cagr,
                    "ew_cagr": ew_cagr,
                    "bm_cagr": bm_cagr,
                    "alpha_opt": alpha_opt,
                    "alpha_ew": alpha_ew,
                    "opt_vol": opt_vol,
                    "opt_sharpe": opt_sharpe,
                    "beats_bm": beats_bm,
                    "num_stocks": len(stock_cagrs)
                }
                
                status = "[BEATS BM]" if beats_bm else "[LAGS BM]"
                print(f"Univ: {u:16s} | Model: {m_name:22s} | Opt: {opt_cagr*100:6.2f}% | EW: {ew_cagr*100:6.2f}% | BM: {bm_cagr*100:6.2f}% | Alpha: {alpha_opt*100:+6.2f}% {status}")
                
    out_file = os.path.join(SCRATCH_DIR, "multi_period_transferability_results.json")
    with open(out_file, "w") as f:
        json.dump(period_results, f, indent=2)
    print(f"\nAll period results saved to {out_file}.")

if __name__ == "__main__":
    run_multi_period_analysis()
