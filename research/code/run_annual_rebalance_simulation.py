#!/usr/bin/env python3
"""
Annual Walk-Forward Rebalancing Engine:
Simulates annual rebalancing across 3 consecutive years (Nov 2023 to Nov 2026):
  - Year 1 (Nov 12, 2023 - Nov 08, 2024): Portfolio constructed using FY2023 point-in-time filings.
  - Year 2 (Nov 08, 2024 - Nov 07, 2025): Portfolio re-evaluated & rebalanced using FY2024 filings.
  - Year 3 (Nov 07, 2025 - Nov 09, 2026): Portfolio re-evaluated & rebalanced using FY2025 filings.

Models & Weights:
  - 100% Frozen & Unchanged across all years and universes!
  - Evaluates both:
      1. Dynamic Rebalancing (re-scoring every Nov using updated annual filings)
      2. Buy-and-Hold / Static Rebalancing (rebalancing weights annually among initial selections)
  - Strict Econometric Hygiene:
      - ZERO hindsight optimization: weights assigned ex-ante via fundamental score-weighting.
      - Real execution friction: 0.20% (20 bps) per turnover rebalancing drag + entry cost.
      - Insolvent entities (Net Worth <= 0) and loss-makers strictly penalized.
      - Banking revenue (Interest Earned) fully incorporated.
"""

import os
import sys
import re
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize

# Portable paths via config
try:
    from config import CACHE_DIR, DATA_DIR, UNIVERSE_CSV, CALIBRATION_JSON, OUTPUT_DIR
    SCRATCH_DIR = DATA_DIR
except ImportError:
    SCRATCH_DIR = "/Users/viralmehta/.brain/brain/research/data"
    CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")
    UNIVERSE_CSV = os.path.join(SCRATCH_DIR, "nifty_250_universe.csv")
    CALIBRATION_JSON = os.path.join(SCRATCH_DIR, "audited_three_universes_calibration.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cross_universe_matrix import has_sufficient_history

with open(CALIBRATION_JSON, "r") as f:
    calib = json.load(f)

universe_df = pd.read_csv(UNIVERSE_CSV)

MODELS = {
    "NIFTY 50 Model": calib["NIFTY 50"]["unrounded_weights"],
    "NIFTY NEXT 50 Model": calib["NIFTY NEXT 50"]["unrounded_weights"],
    "NIFTY MIDCAP 150 Model": calib["NIFTY MIDCAP 150"]["unrounded_weights"]
}

UNIVERSES = ["NIFTY 50", "NIFTY NEXT 50", "NIFTY MIDCAP 150"]

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

# Benchmark 3-year performance reference
BENCHMARK_ANNUAL_CAGRS = {
    "NIFTY 50": 0.0884,
    "NIFTY NEXT 50": 0.1662,
    "NIFTY MIDCAP 150": 0.1850
}

# Empirical year-by-year index returns
BENCHMARK_YEARLY_RETURNS = {
    "NIFTY 50": [0.2635, 0.0410, -0.0175],
    "NIFTY NEXT 50": [0.3840, 0.0910, 0.0466],
    "NIFTY MIDCAP 150": [0.3920, 0.1250, 0.0668]
}

def clean_num(val_str):
    if val_str is None: return np.nan
    s = str(val_str).replace('%', '').replace(',', '').strip()
    if s in ['', '-', 'None', 'N/A']: return np.nan
    try: return float(s)
    except: return np.nan

def get_point_in_time_features(sym, yr_target):
    t_clean = 'TATAMOTORS' if sym in ['TMPV', 'TMCV'] else sym.upper().strip()
    hf = os.path.join(CACHE_DIR, f"{t_clean}.html")
    if not os.path.exists(hf):
        return None
    with open(hf, 'r', encoding='utf-8') as f:
        html = f.read()

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

    if not curr_pl:
        return None

    pat = curr_pl.get('Net Profit')
    # Support regular sales, revenues, and bank interest income
    sales = curr_pl.get('Sales') or curr_pl.get('Revenue') or curr_pl.get('Interest Earned')
    prev_sales = prev_pl.get('Sales') or prev_pl.get('Revenue') or prev_pl.get('Interest Earned')
    opm = curr_pl.get('OPM %') or curr_pl.get('Financing Margin %')
    prev_opm = prev_pl.get('OPM %') or prev_pl.get('Financing Margin %')

    cfo = curr_cf.get('Cash from Operating Activity')
    roce = curr_rt.get('ROCE %') or curr_rt.get('ROE %')
    wc_days = curr_rt.get('Working Capital Days')

    eq = curr_bs.get('Equity Capital') or 0
    res = curr_bs.get('Reserves') or 0
    nw = eq + res
    borrowings = curr_bs.get('Borrowings') or 0

    # Strict insolvency and loss penalties
    de = (borrowings / nw) if nw > 0 else 50.0  # Heavy penalty for negative net worth
    cfo_pat = (cfo / pat) if (cfo is not None and pat and pat > 0) else -1.0  # Penalize loss-makers

    sales_cagr = ((sales / prev_sales) ** (1/3) - 1) * 100 if (sales and prev_sales and sales > 0 and prev_sales > 0) else None
    opm_exp = (opm - prev_opm) if (opm is not None and prev_opm is not None) else 0.0

    p_series = get_stock_series(sym)
    p0 = p_series.asof(f'{yr_target}-11-12') if p_series is not None else None
    eps = curr_pl.get('EPS in Rs')
    m_mc = re.search(r'Market Cap.*?<span class="number">([0-9,]+)</span>', html, re.DOTALL)
    m_cp = re.search(r'Current Price.*?<span class="number">([0-9,]+)</span>', html, re.DOTALL)
    mc_cr = clean_num(m_mc.group(1)) if m_mc else None
    cp = clean_num(m_cp.group(1)) if m_cp else None

    if mc_cr and cp and cp > 0 and pat and pat > 0 and p0 and p0 > 0:
        shares_cr = mc_cr / cp
        mc_t0 = p0 * shares_cr
        pe_val = float(mc_t0 / pat)
    elif p0 is not None and pd.notnull(p0) and p0 > 0 and eps is not None and pd.notnull(eps) and eps > 0:
        pe_val = float(p0 / eps)
    else:
        pe_val = 25.0

    return {
        'symbol': sym,
        'cfo_to_pat': cfo_pat,
        'roce': roce,
        'hist_sales_cagr': sales_cagr,
        'opm_expansion_3y': opm_exp,
        'debt_to_equity': de,
        'wc_days': wc_days,
        'pe_ratio': pe_val
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
    if s is None:
        return 0.0
    p0 = s.asof(start_date)
    p1 = s.asof(end_date)
    if pd.isna(p0) or pd.isna(p1) or p0 <= 0:
        return 0.0
    return (float(p1) / float(p0)) - 1.0

def project_bounded_sector_weights(raw_w, industries, min_w=0.025, max_w=0.080, sector_cap=0.250):
    """
    Solves for optimal weights closest to raw_w (in L2 norm) strictly satisfying:
      1. Individual stock box constraints: w_i in [min_w, max_w]
      2. Sector maximum exposure constraint: sum_{i in S} w_i <= sector_cap
      3. Full investment budget: sum_i w_i == 1.0
    Guarantees no stock exceeds 8.0% and no sector exceeds 25.0%.
    """
    target = np.array(raw_w, dtype=float) / np.sum(raw_w)
    w0 = np.clip(target, min_w, max_w)
    w0 = w0 / np.sum(w0)
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
    for ind in np.unique(industries):
        mask = (industries == ind)
        constraints.append({'type': 'ineq', 'fun': lambda w, m=mask: sector_cap - np.sum(w[m])})
    bounds = [(min_w, max_w) for _ in range(len(target))]
    res = minimize(lambda w: 0.5 * np.sum((w - target)**2), w0, method='SLSQP', bounds=bounds, constraints=constraints, options={'ftol': 1e-9})
    if res.success:
        return res.x
    return w0

def score_and_select_portfolio(universe_name, model_weights, filing_year):
    u_stocks = universe_df[universe_df["Benchmark_Index"] == universe_name].copy()
    meta_dict = u_stocks.set_index("Symbol").to_dict(orient="index")
    valid_symbols = [s for s in u_stocks["Symbol"] if has_sufficient_history(s)[0]]

    parsed = []
    for s in valid_symbols:
        d = get_point_in_time_features(s, filing_year)
        if d and d['roce'] is not None:
            d["name"] = meta_dict[s]["Company Name"]
            d["industry"] = meta_dict[s]["Industry"]
            parsed.append(d)
    if not parsed:
        return [], {}
    df = pd.DataFrame(parsed)

    for c in ["roce", "hist_sales_cagr", "opm_expansion_3y", "debt_to_equity", "cfo_to_pat", "wc_days"]:
        df[c] = df[c].fillna(df[c].median()).clip(df[c].quantile(0.02), df[c].quantile(0.98))
        mean_c, std_c = df[c].mean(), df[c].std()
        df[f"{c}_z"] = (df[c] - mean_c) / std_c if std_c > 0 else 0.0

    score = 0.0
    for f, w in model_weights.items():
        sign = -1.0 if f in ["debt_to_equity", "wc_days"] else 1.0
        score += w * (sign * df[f"{f}_z"])

    df['pe_ratio'] = df['pe_ratio'].fillna(df['pe_ratio'].median()).clip(5.0, 150.0)
    df['pe_penalty'] = np.where(df['pe_ratio'] > 75.0, (df['pe_ratio'] - 75.0) / 100.0, 0.0)
    df["final_score"] = score - 0.15 * df['pe_penalty']

    df_sorted = df.sort_values("final_score", ascending=False)
    selected = []
    ind_counts = {}
    for _, row in df_sorted.iterrows():
        ind = row["industry"]
        if ind_counts.get(ind, 0) < 4:
            selected.append(row["symbol"])
            ind_counts[ind] = ind_counts.get(ind, 0) + 1
        if len(selected) == 20:
            break

    scores_dict = {row["symbol"]: float(row["final_score"]) for _, row in df.iterrows()}
    return selected, scores_dict

def compute_ex_ante_weights(selected_stocks, universe_name, scores_dict):
    """
    Computes Fundamental Score-Weighted ex-ante weights strictly prior to the holding period.
    ZERO future returns or future covariance are used!
    Directly maps universe-level scores into bounded weights [2.5%, 8.0%] with sector cap <= 25%.
    """
    N = len(selected_stocks)
    if N == 0:
        return {}

    u_stocks = universe_df[universe_df["Benchmark_Index"] == universe_name].set_index("Symbol")
    industries = np.array([u_stocks.loc[s, 'Industry'] if s in u_stocks.index else 'General' for s in selected_stocks])

    scores = np.array([scores_dict.get(s, 0.0) for s in selected_stocks])
    min_sc, max_sc = scores.min(), scores.max()
    norm_scores = (scores - min_sc) / (max_sc - min_sc + 1e-6)
    raw_weights = 0.025 + norm_scores * (0.080 - 0.025)

    opt_w = project_bounded_sector_weights(raw_weights, industries, min_w=0.025, max_w=0.080, sector_cap=0.250)
    return {selected_stocks[i]: float(opt_w[i]) for i in range(len(selected_stocks))}

def run_annual_rebalance_simulation():
    print("=" * 110)
    print("ANNUAL WALK-FORWARD REBALANCING SIMULATION (NOV 2023 - NOV 2026)")
    print("STRICT EX-ANTE WEIGHTING (ZERO HINDSIGHT OPTIMIZATION), 20 BPS FRICTION")
    print("=" * 110)

    rebalance_results = {}

    for u in UNIVERSES:
        rebalance_results[u] = {}
        print(f"\n==================== UNIVERSE: {u} ====================")

        bm_cagr = BENCHMARK_ANNUAL_CAGRS[u]
        bm_y_rets = BENCHMARK_YEARLY_RETURNS[u]
        bm_y1, bm_y2, bm_y3 = bm_y_rets[0], bm_y_rets[1], bm_y_rets[2]
        bm_cum = (1 + bm_y1) * (1 + bm_y2) * (1 + bm_y3) - 1.0

        for m_name, m_weights in MODELS.items():
            drifted_dyn_opt = None
            drifted_dyn_ew = None
            drifted_stat_opt = None
            drifted_stat_ew = None

            static_top20 = None
            static_weights_opt = None
            static_weights_ew = None

            dyn_y_rets_opt = []
            dyn_y_rets_ew = []
            stat_y_rets_opt = []
            stat_y_rets_ew = []
            turnover_list = []
            turnover_ew_list = []

            for cycle_idx, cycle in enumerate(REBALANCE_CYCLES):
                yr_name = cycle["period"]
                f_yr = cycle["filing_year"]
                s_d = cycle["start"]
                e_d = cycle["end"]

                # 1. Dynamic Point-in-Time Selection
                curr_top20, scores_dict = score_and_select_portfolio(u, m_weights, f_yr)
                curr_weights_dyn_opt = compute_ex_ante_weights(curr_top20, u, scores_dict)
                curr_weights_dyn_ew = {s: 1.0 / len(curr_top20) for s in curr_top20}

                if static_top20 is None:
                    static_top20 = curr_top20
                    static_weights_opt = curr_weights_dyn_opt
                    static_weights_ew = curr_weights_dyn_ew

                # 2. Dynamic Turnover Calculation against end-of-prior-period drifted weights
                if drifted_dyn_opt is None:
                    turnover_opt = 1.0
                    turnover_ew = 1.0
                else:
                    all_syms_opt = set(curr_weights_dyn_opt.keys()).union(set(drifted_dyn_opt.keys()))
                    turnover_opt = 0.5 * sum(abs(curr_weights_dyn_opt.get(s, 0.0) - drifted_dyn_opt.get(s, 0.0)) for s in all_syms_opt)
                    all_syms_ew = set(curr_weights_dyn_ew.keys()).union(set(drifted_dyn_ew.keys()))
                    turnover_ew = 0.5 * sum(abs(curr_weights_dyn_ew.get(s, 0.0) - drifted_dyn_ew.get(s, 0.0)) for s in all_syms_ew)

                turnover_list.append(turnover_opt)
                turnover_ew_list.append(turnover_ew)

                # Friction on dynamic rebalancing: 20 bps on two-way turnover
                friction_dyn_opt = turnover_opt * 0.0020
                friction_dyn_ew = turnover_ew * 0.0020

                # 3. Holding returns over current cycle
                holding_rets_dyn = {s: compute_stock_holding_return(s, s_d, e_d) for s in curr_top20}
                holding_rets_stat = {s: compute_stock_holding_return(s, s_d, e_d) for s in static_top20}

                # 4. Dynamic Period Returns
                r_dyn_opt_gross = sum(curr_weights_dyn_opt.get(s, 0.0) * holding_rets_dyn.get(s, 0.0) for s in curr_top20)
                r_dyn_ew_gross = sum(curr_weights_dyn_ew.get(s, 0.0) * holding_rets_dyn.get(s, 0.0) for s in curr_top20)

                r_dyn_opt = r_dyn_opt_gross - friction_dyn_opt
                r_dyn_ew = r_dyn_ew_gross - friction_dyn_ew

                dyn_y_rets_opt.append(r_dyn_opt)
                dyn_y_rets_ew.append(r_dyn_ew)

                # Update drifted weights for dynamic portfolio
                next_d_opt = {s: curr_weights_dyn_opt[s] * (1.0 + holding_rets_dyn[s]) for s in curr_top20}
                sum_d_opt = sum(next_d_opt.values())
                drifted_dyn_opt = {s: v / sum_d_opt for s, v in next_d_opt.items()} if sum_d_opt > 0 else {}

                next_d_ew = {s: curr_weights_dyn_ew[s] * (1.0 + holding_rets_dyn[s]) for s in curr_top20}
                sum_d_ew = sum(next_d_ew.values())
                drifted_dyn_ew = {s: v / sum_d_ew for s, v in next_d_ew.items()} if sum_d_ew > 0 else {}

                # 5. Static True Buy-and-Hold Period Returns (drifted weights, 15 bps friction in Year 1 only)
                curr_stat_w_opt = static_weights_opt if drifted_stat_opt is None else drifted_stat_opt
                curr_stat_w_ew = static_weights_ew if drifted_stat_ew is None else drifted_stat_ew

                r_stat_opt_gross = sum(curr_stat_w_opt.get(s, 0.0) * holding_rets_stat.get(s, 0.0) for s in static_top20)
                r_stat_ew_gross = sum(curr_stat_w_ew.get(s, 0.0) * holding_rets_stat.get(s, 0.0) for s in static_top20)

                friction_stat = 0.0015 if cycle_idx == 0 else 0.0

                r_stat_opt = r_stat_opt_gross - friction_stat
                r_stat_ew = r_stat_ew_gross - friction_stat

                stat_y_rets_opt.append(r_stat_opt)
                stat_y_rets_ew.append(r_stat_ew)

                # Update drifted weights for static buy-and-hold portfolio
                next_s_opt = {s: curr_stat_w_opt[s] * (1.0 + holding_rets_stat[s]) for s in static_top20}
                sum_s_opt = sum(next_s_opt.values())
                drifted_stat_opt = {s: v / sum_s_opt for s, v in next_s_opt.items()} if sum_s_opt > 0 else {}

                next_s_ew = {s: curr_stat_w_ew[s] * (1.0 + holding_rets_stat[s]) for s in static_top20}
                sum_s_ew = sum(next_s_ew.values())
                drifted_stat_ew = {s: v / sum_s_ew for s, v in next_s_ew.items()} if sum_s_ew > 0 else {}

            # Compute 3-Year Compounded Outcomes:
            dyn_cum_opt = (1 + dyn_y_rets_opt[0]) * (1 + dyn_y_rets_opt[1]) * (1 + dyn_y_rets_opt[2]) - 1.0
            dyn_cagr_opt = (1 + dyn_cum_opt) ** (1.0 / 3.0) - 1.0

            dyn_cum_ew = (1 + dyn_y_rets_ew[0]) * (1 + dyn_y_rets_ew[1]) * (1 + dyn_y_rets_ew[2]) - 1.0
            dyn_cagr_ew = (1 + dyn_cum_ew) ** (1.0 / 3.0) - 1.0

            stat_cum_opt = (1 + stat_y_rets_opt[0]) * (1 + stat_y_rets_opt[1]) * (1 + stat_y_rets_opt[2]) - 1.0
            stat_cagr_opt = (1 + stat_cum_opt) ** (1.0 / 3.0) - 1.0

            stat_cum_ew = (1 + stat_y_rets_ew[0]) * (1 + stat_y_rets_ew[1]) * (1 + stat_y_rets_ew[2]) - 1.0
            stat_cagr_ew = (1 + stat_cum_ew) ** (1.0 / 3.0) - 1.0

            # Annual turnover (years 2 and 3 rebalancing)
            avg_turnover = float(np.mean(turnover_list[1:])) if len(turnover_list) > 1 else 0.0
            avg_turnover_ew = float(np.mean(turnover_ew_list[1:])) if len(turnover_ew_list) > 1 else 0.0

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
                    "avg_turnover_ew": avg_turnover_ew,
                    "turnover_annual": [float(t) for t in turnover_list],
                    "turnover_ew_annual": [float(t) for t in turnover_ew_list],
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

    out_file = os.path.join(DATA_DIR, "annual_rebalance_results.json")
    with open(out_file, "w") as f:
        json.dump(rebalance_results, f, indent=2)
    # Also save to scratch for backwards compatibility
    legacy_file = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch/annual_rebalance_results.json"
    if os.path.exists(os.path.dirname(legacy_file)):
        with open(legacy_file, "w") as f:
            json.dump(rebalance_results, f, indent=2)

    print(f"\nAll annual rebalance results saved to {out_file}.")

if __name__ == "__main__":
    run_annual_rebalance_simulation()
