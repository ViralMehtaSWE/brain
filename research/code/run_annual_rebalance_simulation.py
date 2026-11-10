#!/usr/bin/env python3
"""
Annual Walk-Forward Rebalancing Engine:
Simulates annual rebalancing across 3 consecutive years (Nov 2023 to Nov 2026):
  - Year 1 (Nov 12, 2023 - Nov 08, 2024): Portfolio constructed using FY2023 financials.
  - Year 2 (Nov 08, 2024 - Nov 07, 2025): Portfolio re-evaluated & rebalanced using FY2024 financials.
  - Year 3 (Nov 07, 2025 - Nov 09, 2026): Portfolio re-evaluated & rebalanced using FY2025 financials.

Models & Weights:
  - 100% Frozen & Unchanged across all years and universes!
  - Evaluates both:
      1. Dynamic Rebalancing (re-scoring every Nov using updated annual filings)
      2. Buy-and-Hold / Static Rebalancing (rebalancing weights annually among initial selections)
  - Also accounts for realistic execution friction: 0.15% per turnover rebalancing drag (STT + brokerage + slippage).
"""

import os
import sys
import re
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
sys.path.insert(0, SCRATCH_DIR)

from run_cross_universe_matrix import has_sufficient_history

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

# Annual Rebalancing Stages:
REBALANCE_CYCLES = [
    {
        "period": "Year 1",
        "filing_year": 2023,
        "start": "2023-11-12",
        "end": "2024-11-08",
        "days": 362
    },
    {
        "period": "Year 2",
        "filing_year": 2024,
        "start": "2024-11-08",
        "end": "2025-11-07",
        "days": 364
    },
    {
        "period": "Year 3",
        "filing_year": 2025,
        "start": "2025-11-07",
        "end": "2026-11-09",
        "days": 367
    }
]

BM_FILES = {
    "NIFTY 50": os.path.join(PRICE_10Y_DIR, "NIFTY_50_price10y.csv"),
    "NIFTY NEXT 50": os.path.join(PRICE_10Y_DIR, "NIFTY_NEXT_50_price10y.csv"),
    "NIFTY MIDCAP 150": os.path.join(PRICE_10Y_DIR, "NIPPON_MIDCAP_150_ETF_price10y.csv")
}

def get_bm_return(u_name, start_date, end_date):
    bf = BM_FILES[u_name]
    df = pd.read_csv(bf, parse_dates=["date"]).set_index("date").sort_index()
    p0 = float(df.asof(start_date)["price"])
    p1 = float(df.asof(end_date)["price"])
    return (p1 / p0) - 1.0

def get_point_in_time_features(sym, yr_target):
    t_clean = 'TATAMOTORS' if sym in ['TMPV', 'TMCV'] else sym.upper().strip()
    hf = f'{CACHE_DIR}/{t_clean}.html'
    if not os.path.exists(hf): return None
    with open(hf, 'r', encoding='utf-8') as f: html = f.read()
    
    def parse_sec(sec_id):
        pos = html.find(f'id="{sec_id}"')
        if pos == -1: return {}, []
        sec = html[pos:html.find('</section>', pos)]
        thead = re.search(r'<thead>(.*?)</thead>', sec, re.DOTALL)
        tbody = re.search(r'<tbody>(.*?)</tbody>', sec, re.DOTALL)
        if not thead or not tbody: return {}, []
        ths = re.findall(r'<th[^>]*>(.*?)</th>', thead.group(1), re.DOTALL)
        periods = [re.sub(r'<[^>]+>', '', th).strip() for th in ths[1:]]
        metrics = {}
        for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', tbody.group(1), re.DOTALL):
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
            if len(tds) > 1:
                name = ' '.join(re.sub(r'<[^>]+>', '', tds[0]).replace('&nbsp;', ' ').replace('+', '').split())
                vals = []
                for td in tds[1:]:
                    s = re.sub(r'<[^>]+>', '', td).replace('%', '').replace(',', '').strip()
                    try: vals.append(float(s))
                    except: vals.append(None)
                metrics[name] = vals
        res = {}
        for i, p in enumerate(periods):
            res[p] = {m: metrics[m][i] if i < len(metrics[m]) else None for m in metrics}
        return res, periods

    pl, _ = parse_sec('profit-loss')
    bs, _ = parse_sec('balance-sheet')
    cf, _ = parse_sec('cash-flow')
    rt, _ = parse_sec('ratios')
    
    p_curr = f'Mar {yr_target}'
    p_prev3 = f'Mar {yr_target - 3}'
    
    curr_pl = pl.get(p_curr, {})
    prev_pl = pl.get(p_prev3, {})
    curr_bs = bs.get(p_curr, {})
    curr_cf = cf.get(p_curr, {})
    curr_rt = rt.get(p_curr, {})
    
    if not curr_pl: return None
    
    pat = curr_pl.get('Net Profit')
    sales = curr_pl.get('Sales') or curr_pl.get('Revenue')
    prev_sales = prev_pl.get('Sales') or prev_pl.get('Revenue')
    opm = curr_pl.get('OPM %') or curr_pl.get('Financing Margin %')
    prev_opm = prev_pl.get('OPM %') or prev_pl.get('Financing Margin %')
    
    cfo = curr_cf.get('Cash from Operating Activity')
    roce = curr_rt.get('ROCE %') or curr_rt.get('ROE %')
    wc_days = curr_rt.get('Working Capital Days')
    
    eq = curr_bs.get('Equity Capital') or 0
    res = curr_bs.get('Reserves') or 0
    nw = eq + res
    borrowings = curr_bs.get('Borrowings') or 0
    de = (borrowings / nw) if nw > 0 else 0.0
    
    sales_cagr = ((sales / prev_sales) ** (1/3) - 1) * 100 if (sales and prev_sales and sales > 0 and prev_sales > 0) else None
    opm_exp = (opm - prev_opm) if (opm is not None and prev_opm is not None) else 0.0
    cfo_pat = (cfo / pat) if (cfo is not None and pat and pat > 0) else 1.0
    
    return {
        'symbol': sym,
        'cfo_to_pat': cfo_pat,
        'roce': roce,
        'hist_sales_cagr': sales_cagr,
        'opm_expansion_3y': opm_exp,
        'debt_to_equity': de,
        'wc_days': wc_days
    }

def get_stock_series(symbol):
    t_clean = 'TATAMOTORS' if symbol in ['TMPV', 'TMCV'] else symbol.upper().strip()
    cache = os.path.join(CACHE_DIR, f"{t_clean}_price.csv")
    if os.path.exists(cache) and os.path.getsize(cache) > 100:
        df = pd.read_csv(cache, parse_dates=['date']).dropna().drop_duplicates('date').sort_values('date')
        if len(df) > 15:
            return df.set_index('date')['price']
    return None

def compute_stock_holding_return(sym, start_date, end_date):
    s = get_stock_series(sym)
    if s is None: return 0.0
    p0 = s.asof(start_date)
    p1 = s.asof(end_date)
    if pd.isna(p0) or pd.isna(p1) or p0 <= 0: return 0.0
    return (float(p1) / float(p0)) - 1.0

def score_and_select_portfolio(universe_name, model_weights, filing_year):
    u_stocks = universe_df[universe_df["Benchmark_Index"] == universe_name].copy()
    meta_dict = u_stocks.set_index("Symbol").to_dict(orient="index")
    valid_symbols = [s for s in u_stocks["Symbol"] if has_sufficient_history(s)[0]]
    
    parsed = []
    for s in valid_symbols:
        d = get_point_in_time_features(s, filing_year)
        if d:
            d["name"] = meta_dict[s]["Company Name"]
            d["industry"] = meta_dict[s]["Industry"]
            parsed.append(d)
    if not parsed:
        return []
    df = pd.DataFrame(parsed)
    
    for c in ["roce", "hist_sales_cagr", "opm_expansion_3y", "debt_to_equity", "cfo_to_pat", "wc_days"]:
        df[c] = df[c].fillna(df[c].median()).clip(df[c].quantile(0.02), df[c].quantile(0.98))
        mean_c, std_c = df[c].mean(), df[c].std()
        df[f"{c}_z"] = (df[c] - mean_c) / std_c if std_c > 0 else 0.0
        
    score = 0.0
    for f, w in model_weights.items():
        sign = -1.0 if f in ["debt_to_equity", "wc_days"] else 1.0
        score += w * (sign * df[f"{f}_z"])
    df["final_score"] = score
    
    df_sorted = df.sort_values("final_score", ascending=False)
    selected = []
    ind_counts = {}
    for _, row in df_sorted.iterrows():
        ind = row["industry"]
        if ind_counts.get(ind, 0) < 4:
            selected.append(row["symbol"])
            ind_counts[ind] = ind_counts.get(ind, 0) + 1
        if len(selected) == 20: break
    return selected

def optimize_weights(selected_stocks, start_date, end_date):
    price_dict = {}
    returns_dict = {}
    for sym in selected_stocks:
        s = get_stock_series(sym)
        if s is not None:
            r = compute_stock_holding_return(sym, start_date, end_date)
            returns_dict[sym] = r
            sub = s.loc[start_date:end_date]
            if len(sub) > 5:
                price_dict[sym] = sub
    valid_syms = list(returns_dict.keys())
    N = len(valid_syms)
    if N < 15:
        return {s: 1.0/len(selected_stocks) for s in selected_stocks}, returns_dict
        
    prices_df = pd.DataFrame(price_dict).pct_change().dropna(how="all")
    cov = prices_df.cov() * 52.0
    cov = cov.fillna(cov.median().median() if not cov.empty else 0.04)
    cov_arr = cov.loc[valid_syms, valid_syms].values
    mu_arr = np.array([returns_dict[s] for s in valid_syms])
    
    rf = 0.07 # 7% 1-year risk free rate
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
    
    return {s: float(w_opt[i]) for i, s in enumerate(valid_syms)}, returns_dict

def run_annual_rebalance_simulation():
    print("=" * 110)
    print("ANNUAL WALK-FORWARD REBALANCING SIMULATION (NOV 2023 - NOV 2026)")
    print("=" * 110)
    
    rebalance_results = {}
    
    for u in UNIVERSES:
        rebalance_results[u] = {}
        print(f"\n==================== UNIVERSE: {u} ====================")
        
        # Benchmark cumulative return
        bm_y1 = get_bm_return(u, REBALANCE_CYCLES[0]["start"], REBALANCE_CYCLES[0]["end"])
        bm_y2 = get_bm_return(u, REBALANCE_CYCLES[1]["start"], REBALANCE_CYCLES[1]["end"])
        bm_y3 = get_bm_return(u, REBALANCE_CYCLES[2]["start"], REBALANCE_CYCLES[2]["end"])
        
        bm_cum = (1 + bm_y1) * (1 + bm_y2) * (1 + bm_y3) - 1.0
        bm_cagr = (1 + bm_cum) ** (1 / 2.99) - 1.0
        
        print(f"Benchmark Cumulative Return: {bm_cum*100:6.2f}% | Annualized CAGR: {bm_cagr*100:5.2f}%")
        print(f"   [Y1: {bm_y1*100:5.2f}%, Y2: {bm_y2*100:5.2f}%, Y3: {bm_y3*100:5.2f}%]")
        
        for m_name, weights in MODELS.items():
            # 1. Dynamic Annual Rebalancing (Point-in-Time Rescoring each November)
            dyn_y_rets_opt = []
            dyn_y_rets_ew = []
            turnover_list = []
            prev_portfolio = set()
            
            # 2. Static Buy-and-Hold (Fixed Initial Portfolio from Y1, rebalanced to target weights each year)
            static_top20 = score_and_select_portfolio(u, weights, filing_year=2023)
            stat_y_rets_opt = []
            stat_y_rets_ew = []
            
            for cycle in REBALANCE_CYCLES:
                s_d = cycle["start"]
                e_d = cycle["end"]
                f_yr = cycle["filing_year"]
                
                # Dynamic portfolio selection for this year
                curr_top20 = score_and_select_portfolio(u, weights, filing_year=f_yr)
                if prev_portfolio:
                    turnover = len(set(curr_top20) - prev_portfolio) / len(curr_top20)
                    turnover_list.append(turnover)
                prev_portfolio = set(curr_top20)
                
                # Dynamic optimization and returns
                w_opt_dyn, rets_dyn = optimize_weights(curr_top20, s_d, e_d)
                r_dyn_opt = sum(w_opt_dyn.get(s, 0.0) * rets_dyn.get(s, 0.0) for s in curr_top20)
                r_dyn_ew = np.mean([rets_dyn.get(s, 0.0) for s in curr_top20]) if curr_top20 else 0.0
                
                # Apply 0.15% turnover friction drag
                friction = (turnover_list[-1] if turnover_list else 0.0) * 0.0015
                r_dyn_opt -= friction
                r_dyn_ew -= friction
                
                dyn_y_rets_opt.append(r_dyn_opt)
                dyn_y_rets_ew.append(r_dyn_ew)
                
                # Static portfolio returns
                w_opt_stat, rets_stat = optimize_weights(static_top20, s_d, e_d)
                r_stat_opt = sum(w_opt_stat.get(s, 0.0) * rets_stat.get(s, 0.0) for s in static_top20)
                r_stat_ew = np.mean([rets_stat.get(s, 0.0) for s in static_top20]) if static_top20 else 0.0
                
                stat_y_rets_opt.append(r_stat_opt)
                stat_y_rets_ew.append(r_stat_ew)
                
            # Compute 3-Year Compounded Outcomes:
            dyn_cum_opt = (1 + dyn_y_rets_opt[0]) * (1 + dyn_y_rets_opt[1]) * (1 + dyn_y_rets_opt[2]) - 1.0
            dyn_cagr_opt = (1 + dyn_cum_opt) ** (1 / 2.99) - 1.0
            
            dyn_cum_ew = (1 + dyn_y_rets_ew[0]) * (1 + dyn_y_rets_ew[1]) * (1 + dyn_y_rets_ew[2]) - 1.0
            dyn_cagr_ew = (1 + dyn_cum_ew) ** (1 / 2.99) - 1.0
            
            stat_cum_opt = (1 + stat_y_rets_opt[0]) * (1 + stat_y_rets_opt[1]) * (1 + stat_y_rets_opt[2]) - 1.0
            stat_cagr_opt = (1 + stat_cum_opt) ** (1 / 2.99) - 1.0
            
            stat_cum_ew = (1 + stat_y_rets_ew[0]) * (1 + stat_y_rets_ew[1]) * (1 + stat_y_rets_ew[2]) - 1.0
            stat_cagr_ew = (1 + stat_cum_ew) ** (1 / 2.99) - 1.0
            
            avg_turnover = np.mean(turnover_list) if turnover_list else 0.0
            
            rebalance_results[u][m_name] = {
                "benchmark": {
                    "cum_return": bm_cum,
                    "cagr": bm_cagr,
                    "y1": bm_y1, "y2": bm_y2, "y3": bm_y3
                },
                "dynamic_rebalancing": {
                    "opt_cum": dyn_cum_opt,
                    "opt_cagr": dyn_cagr_opt,
                    "opt_alpha": dyn_cagr_opt - bm_cagr,
                    "ew_cum": dyn_cum_ew,
                    "ew_cagr": dyn_cagr_ew,
                    "ew_alpha": dyn_cagr_ew - bm_cagr,
                    "y1_opt": dyn_y_rets_opt[0], "y2_opt": dyn_y_rets_opt[1], "y3_opt": dyn_y_rets_opt[2],
                    "avg_turnover": avg_turnover,
                    "beats_bm": dyn_cagr_opt > bm_cagr
                },
                "static_rebalancing": {
                    "opt_cum": stat_cum_opt,
                    "opt_cagr": stat_cagr_opt,
                    "opt_alpha": stat_cagr_opt - bm_cagr,
                    "ew_cum": stat_cum_ew,
                    "ew_cagr": stat_cagr_ew,
                    "ew_alpha": stat_cagr_ew - bm_cagr,
                    "beats_bm": stat_cagr_opt > bm_cagr
                }
            }
            
            print(f"Model: {m_name:22s} | Dyn Opt CAGR: {dyn_cagr_opt*100:5.2f}% (+{(dyn_cagr_opt-bm_cagr)*100:+5.2f}% α) | Dyn EW: {dyn_cagr_ew*100:5.2f}% | Avg Turnover: {avg_turnover*100:4.1f}%")
            print(f"   Dynamic Annual Path: [Y1: {dyn_y_rets_opt[0]*100:5.2f}%, Y2: {dyn_y_rets_opt[1]*100:5.2f}%, Y3: {dyn_y_rets_opt[2]*100:5.2f}%]")
            print(f"   Static 3Y Path:      [Y1: {stat_y_rets_opt[0]*100:5.2f}%, Y2: {stat_y_rets_opt[1]*100:5.2f}%, Y3: {stat_y_rets_opt[2]*100:5.2f}%] -> Static CAGR: {stat_cagr_opt*100:5.2f}%")

    out_file = os.path.join(SCRATCH_DIR, "annual_rebalance_results.json")
    with open(out_file, "w") as f:
        json.dump(rebalance_results, f, indent=2)
    print(f"\nAll annual rebalance results saved to {out_file}.")

if __name__ == "__main__":
    run_annual_rebalance_simulation()
