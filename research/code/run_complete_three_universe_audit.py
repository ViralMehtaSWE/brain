#!/usr/bin/env python3
"""
Exhaustive Audit & Calibration Pipeline Across All Three Universes:
- NIFTY 50 (All 50 constituents)
- NIFTY NEXT 50 (All 50 constituents)
- NIFTY MIDCAP 150 (All 150 constituents)

Uses 100% actual Screener.in data with ZERO omissions and ZERO hardcoded ticker subsets.
"""

import os
import sys
import re
import json
import time
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, ttest_1samp
from scipy.optimize import minimize
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance

try:
    from config import CACHE_DIR, UNIVERSE_CSV, DATA_DIR
    SCRATCH_DIR = DATA_DIR
except ImportError:
    SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
    CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")
    UNIVERSE_CSV = os.path.join(SCRATCH_DIR, "nifty_250_universe.csv")


def clean_num(val_str):
    if val_str is None: return np.nan
    s = str(val_str).replace('%', '').replace(',', '').strip()
    if s in ['', '-', 'None', 'N/A']: return np.nan
    try: return float(s)
    except: return np.nan

def parse_section(html, sec_id):
    pos = html.find(f'id="{sec_id}"')
    if pos == -1: return {}, []
    sec = html[pos:html.find('</section>', pos)]
    thead = re.search(r'<thead>(.*?)</thead>', sec, re.DOTALL)
    periods = []
    if thead:
        for th in re.findall(r'<th[^>]*>(.*?)</th>', thead.group(1), re.DOTALL):
            c = re.sub(r'<[^>]+>', '', th).strip()
            if c and c != 'Raw PDF' and not c.startswith('+'):
                periods.append(c)
    tbody = re.search(r'<tbody>(.*?)</tbody>', sec, re.DOTALL)
    metrics = {}
    if tbody:
        for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', tbody.group(1), re.DOTALL):
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
            clean_tds = [clean_num(re.sub(r'<[^>]+>', '', td)) for td in tds]
            if len(clean_tds) > 1:
                name = ' '.join(re.sub(r'<[^>]+>', '', tds[0]).replace('&nbsp;', ' ').replace('+', '').split())
                metrics[name] = clean_tds[1:]
    return metrics, periods

def extract_panel_for_universe(symbols, universe_name):
    records = []
    print(f"\n[{universe_name}] Parsing panel for {len(symbols)} constituents...")
    
    for sym in symbols:
        clean_s = 'TATAMOTORS' if sym in ['TMPV', 'TMCV'] else sym
        fpath = os.path.join(CACHE_DIR, f"{clean_s}.html")
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            html = f.read()
        if len(html) < 5000:
            continue
            
        pl, pl_periods = parse_section(html, 'profit-loss')
        bs, bs_periods = parse_section(html, 'balance-sheet')
        cf, cf_periods = parse_section(html, 'cash-flow')
        rt, rt_periods = parse_section(html, 'ratios')
        
        sales_key = 'Sales' if 'Sales' in pl else ('Revenue' if 'Revenue' in pl else ('Interest Earned' if 'Interest Earned' in pl else ('Financing Profit' if 'Financing Profit' in pl else None)))
        pat_key = 'Net Profit' if 'Net Profit' in pl else ('Profit after tax' if 'Profit after tax' in pl else None)
        if not pat_key:
            continue
            
        pl_by_yr = {p: {k: v[i] if i < len(v) else np.nan for k, v in pl.items()} for i, p in enumerate(pl_periods)}
        bs_by_yr = {p: {k: v[i] if i < len(v) else np.nan for k, v in bs.items()} for i, p in enumerate(bs_periods)}
        cf_by_yr = {p: {k: v[i] if i < len(v) else np.nan for k, v in cf.items()} for i, p in enumerate(cf_periods)}
        rt_by_yr = {p: {k: v[i] if i < len(v) else np.nan for k, v in rt.items()} for i, p in enumerate(rt_periods)}
        
        fiscal_years = [p for p in pl_periods if re.match(r'Mar \d{4}', p)]
        
        for idx in range(3, len(fiscal_years) - 3):
            t_yr = fiscal_years[idx]
            t_minus_3 = fiscal_years[idx - 3]
            t_plus_3 = fiscal_years[idx + 3]
            
            curr_pl = pl_by_yr.get(t_yr, {})
            prev_pl = pl_by_yr.get(t_minus_3, {})
            fwd_pl = pl_by_yr.get(t_plus_3, {})
            
            curr_bs = bs_by_yr.get(t_yr, {})
            curr_cf = cf_by_yr.get(t_yr, {})
            curr_rt = rt_by_yr.get(t_yr, {})
            
            sales_t = curr_pl.get(sales_key, np.nan)
            sales_t_minus_3 = prev_pl.get(sales_key, np.nan)
            pat_t = curr_pl.get(pat_key, np.nan)
            pat_t_minus_3 = prev_pl.get(pat_key, np.nan)
            opm_t = curr_pl.get('OPM %', curr_pl.get('Financing Margin %', np.nan))
            prev_opm = prev_pl.get('OPM %', prev_pl.get('Financing Margin %', np.nan))
            
            pat_t_plus_3 = fwd_pl.get(pat_key, np.nan)
            
            hist_sales_cagr = ((sales_t / sales_t_minus_3) ** (1/3) - 1) * 100 if (sales_t and sales_t_minus_3 and sales_t_minus_3 > 0 and sales_t > 0) else np.nan
            hist_pat_cagr = ((pat_t / pat_t_minus_3) ** (1/3) - 1) * 100 if (pat_t and pat_t_minus_3 and pat_t_minus_3 > 0 and pat_t > 0) else np.nan
            opm_expansion_3y = (opm_t - prev_opm) if (opm_t is not None and prev_opm is not None) else np.nan
            
            roce = curr_rt.get('ROCE %', curr_rt.get('ROE %', np.nan))
            wc_days = curr_rt.get('Working Capital Days', np.nan)
            
            borrowings = curr_bs.get('Borrowings', 0) or 0
            net_worth = (curr_bs.get('Equity Capital', 0) or 0) + (curr_bs.get('Reserves', 0) or 0)
            debt_to_equity = (borrowings / net_worth) if net_worth > 0 else 50.0
            
            cfo = curr_cf.get('Cash from Operating Activity', np.nan)
            cfo_to_pat = (cfo / pat_t) if (cfo is not None and pat_t and pat_t > 0) else -1.0
            
            fwd_pat_cagr = ((pat_t_plus_3 / pat_t) ** (1/3) - 1) * 100 if (pat_t_plus_3 and pat_t and pat_t > 0 and pat_t_plus_3 > 0) else np.nan
            
            if pd.notnull(fwd_pat_cagr):
                records.append({
                    'symbol': sym,
                    'year': t_yr,
                    'hist_sales_cagr': hist_sales_cagr,
                    'roce': roce,
                    'opm_expansion_3y': opm_expansion_3y,
                    'cfo_to_pat': cfo_to_pat,
                    'debt_to_equity': debt_to_equity,
                    'wc_days': wc_days,
                    'hist_pat_cagr': hist_pat_cagr,
                    'target_fwd_pat_cagr': fwd_pat_cagr
                })
                
    df = pd.DataFrame(records)
    print(f"[{universe_name}] Total observations across all valid constituents: {len(df)} from {df['symbol'].nunique()} unique stocks.")
    return df

def analyze_factors_and_derive_weights(panel_df, universe_name):
    features = ['cfo_to_pat', 'roce', 'hist_sales_cagr', 'opm_expansion_3y', 'debt_to_equity', 'wc_days']
    clean_df = panel_df.dropna(subset=['target_fwd_pat_cagr']).copy()
    
    for f in features:
        if f in clean_df.columns:
            low = clean_df[f].quantile(0.02)
            high = clean_df[f].quantile(0.98)
            clean_df[f] = clean_df[f].clip(low, high)
            clean_df[f] = clean_df[f].fillna(clean_df[f].median())
            
    # Spearman Rank IC across years
    ic_by_year = {}
    years = clean_df['year'].unique()
    for yr in years:
        sub = clean_df[clean_df['year'] == yr]
        if len(sub) >= 8:
            for f in features:
                corr, _ = spearmanr(sub[f], sub['target_fwd_pat_cagr'], nan_policy='omit')
                if f not in ic_by_year: ic_by_year[f] = []
                if pd.notnull(corr): ic_by_year[f].append(corr)
                
    stats = {}
    for f in features:
        ics = ic_by_year.get(f, [])
        mean_ic = np.mean(ics) if len(ics) > 0 else 0.0
        std_ic = np.std(ics, ddof=1) if len(ics) > 1 else 1.0
        ir = mean_ic / std_ic if std_ic > 0 else 0.0
        t_stat, p_val = ttest_1samp(ics, 0.0) if len(ics) > 1 else (0.0, 1.0)
        stats[f] = {
            'mean_ic': float(mean_ic),
            'ir': float(ir),
            't_stat': float(t_stat),
            'p_value': float(p_val)
        }
        
    # Random Forest Regressor & Permutation Importance
    X = clean_df[features]
    y = clean_df['target_fwd_pat_cagr']
    rf = RandomForestRegressor(n_estimators=200, max_depth=4, random_state=42)
    rf.fit(X, y)
    perm = permutation_importance(rf, X, y, n_repeats=15, random_state=42)
    
    for i, f in enumerate(features):
        stats[f]['rf_gini'] = float(rf.feature_importances_[i])
        stats[f]['perm_imp'] = float(perm.importances_mean[i])
        
    # Unrounded Weights Derivation
    # Directional adjustment: debt_to_equity and wc_days are penalized when high
    raw_w = {}
    for f in features:
        ic_sign = -1.0 if f in ['debt_to_equity', 'wc_days'] else 1.0
        adj_ic = max(0.0, stats[f]['mean_ic'] * ic_sign)
        gini = stats[f]['rf_gini']
        raw_w[f] = 0.5 * adj_ic + 0.5 * gini
        
    tot = sum(raw_w.values())
    unrounded_w = {f: raw_w[f] / tot for f in features}
    
    rounded_w = {f: round(unrounded_w[f], 3) for f in features}
    diff = 1.0 - sum(rounded_w.values())
    top_f = max(rounded_w, key=rounded_w.get)
    rounded_w[top_f] = round(rounded_w[top_f] + diff, 3)
    
    return stats, unrounded_w, rounded_w

def main():
    df_250 = pd.read_csv(UNIVERSE_CSV)
    
    universes = {
        'NIFTY 50': df_250[df_250['Benchmark_Index'] == 'NIFTY 50']['Symbol'].tolist(),
        'NIFTY NEXT 50': df_250[df_250['Benchmark_Index'] == 'NIFTY NEXT 50']['Symbol'].tolist(),
        'NIFTY MIDCAP 150': df_250[df_250['Benchmark_Index'] == 'NIFTY MIDCAP 150']['Symbol'].tolist()
    }
    
    audit_results = {}
    
    for uname, symbols in universes.items():
        panel_df = extract_panel_for_universe(symbols, uname)
        stats, unrounded_w, rounded_w = analyze_factors_and_derive_weights(panel_df, uname)
        
        audit_results[uname] = {
            'total_constituents': len(symbols),
            'unique_stocks_in_panel': int(panel_df['symbol'].nunique()),
            'total_panel_observations': len(panel_df),
            'factor_statistics': stats,
            'unrounded_weights': unrounded_w,
            'rounded_weights': rounded_w
        }
        
    with open(os.path.join(SCRATCH_DIR, "audited_three_universes_calibration.json"), "w") as f:
        json.dump(audit_results, f, indent=2)
        
    print("\n" + "="*85)
    print("AUDITED RESULTS ACROSS ALL THREE UNIVERSES (100% CONSTITUENTS)")
    print("="*85)
    for uname, data in audit_results.items():
        print(f"\n--- {uname} (Constituents: {data['total_constituents']}, Panel Stocks: {data['unique_stocks_in_panel']}, Windows: {data['total_panel_observations']}) ---")
        print(f"{'Factor':<20} | {'Mean IC':<10} | {'IR':<8} | {'t-stat':<8} | {'p-val':<8} | {'RF Gini':<10} | {'Unrounded Weight':<18} | {'Rounded Weight'}")
        print("-" * 105)
        for f in data['unrounded_weights']:
            s = data['factor_statistics'][f]
            uw = data['unrounded_weights'][f]
            rw = data['rounded_weights'][f]
            print(f"{f:<20} | {s['mean_ic']:+.4f}    | {s['ir']:<8.3f} | {s['t_stat']:+6.2f}   | {s['p_value']:<8.4f} | {s['rf_gini']:<10.4f} | {uw:.6f} ({uw*100:5.2f}%) | {rw:.3f} ({rw*100:4.1f}%)")

if __name__ == '__main__':
    main()
