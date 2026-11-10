#!/usr/bin/env python3
"""
Generate Best 10 Stocks and Best 30 Stocks Portfolios across NIFTY 250
Using the NIFTY NEXT 50 Model
Weights:
  - cfo_to_pat       : +36.37%
  - roce             : +26.92%
  - hist_sales_cagr  : +14.92%
  - debt_to_equity   : -11.71%
  - opm_expansion_3y :  +5.70%
  - wc_days          :  -4.37%
"""

import os
import sys
import re
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize

try:
    from config import CACHE_DIR, UNIVERSE_CSV, DATA_DIR, OUTPUT_DIR
    SCRATCH_DIR = DATA_DIR
except ImportError:
    SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
    CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")
    UNIVERSE_CSV = os.path.join(SCRATCH_DIR, "nifty_250_universe.csv")
    OUTPUT_DIR = os.path.join(SCRATCH_DIR, "output")


NEXT50_WEIGHTS = {
    'cfo_to_pat': 0.3637039524478158,
    'roce': 0.2692356057922692,
    'hist_sales_cagr': 0.14918923489820565,
    'debt_to_equity': -0.11714015525796742,
    'opm_expansion_3y': 0.057002639084139474,
    'wc_days': -0.04372841251960261
}

def clean_num(val_str):
    if val_str is None: return np.nan
    s = str(val_str).replace('%', '').replace(',', '').strip()
    if s in ['', '-', 'None', 'N/A']: return np.nan
    try: return float(s)
    except: return np.nan

def has_sufficient_history(symbol, min_price_years=2.8, min_pl_years=3):
    t_clean = 'TATAMOTORS' if symbol in ['TMPV', 'TMCV'] else symbol.upper().strip()
    pf = os.path.join(CACHE_DIR, f"{t_clean}_price.csv")
    hf = os.path.join(CACHE_DIR, f"{t_clean}.html")
    if not os.path.exists(pf) or not os.path.exists(hf):
        return False
    try:
        df = pd.read_csv(pf)
        dcol = [c for c in df.columns if c.lower() == 'date'][0]
        df[dcol] = pd.to_datetime(df[dcol])
        years = (df[dcol].max() - df[dcol].min()).days / 365.25
        if years < min_price_years: return False
    except: return False

    try:
        with open(hf, 'r', encoding='utf-8') as f: html = f.read()
        pos = html.find('id="profit-loss"')
        if pos == -1: return False
        sec = html[pos:html.find('</section>', pos)]
        thead = re.search(r'<thead>(.*?)</thead>', sec, re.DOTALL)
        if not thead: return False
        ths = re.findall(r'<th[^>]*>(.*?)</th>', thead.group(1), re.DOTALL)
        if len(ths) - 1 < min_pl_years: return False
    except: return False

    return True


def parse_latest_fundamentals(symbol, meta_dict):
    t_clean = 'TATAMOTORS' if symbol in ['TMPV', 'TMCV'] else symbol.upper().strip()
    hf = os.path.join(CACHE_DIR, f"{t_clean}.html")
    if not os.path.exists(hf): return None

    with open(hf, 'r', encoding='utf-8') as f: html = f.read()
    if len(html) < 5000: return None

    ratios = {}
    for m in re.finditer(r'<span class=\"name\">\s*([^<]+?)\s*</span>\s*<span class=\"nowrap value\">\s*₹?\s*<span class=\"number\">([^<]+)</span>', html):
        ratios[m.group(1).strip()] = clean_num(m.group(2))

    compound = {}
    for m in re.finditer(r'<table[^>]+class=\"ranges-table\"[^>]*>(.*?)</table>', html, re.DOTALL):
        th = re.search(r'<th[^>]*>(.*?)</th>', m.group(1), re.DOTALL)
        if th:
            title = re.sub(r'<[^>]+>', '', th.group(1)).strip()
            for term, val in re.findall(r'<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>', m.group(1), re.DOTALL):
                compound[f"{title}_{term.replace(':', '').strip()}"] = clean_num(val)

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

    pl, pl_periods = parse_sec('profit-loss')
    bs, _ = parse_sec('balance-sheet')
    cf, _ = parse_sec('cash-flow')
    rt, _ = parse_sec('ratios')

    ann_periods = [p for p in pl_periods if 'TTM' not in p]
    if not ann_periods: return None
    latest_p = ann_periods[-1]
    prev3_idx = len(ann_periods) - 4
    prev3_p = ann_periods[prev3_idx] if prev3_idx >= 0 else ann_periods[0]

    curr_pl = pl.get(latest_p, {})
    prev3_pl = pl.get(prev3_p, {})
    curr_bs = bs.get(latest_p, {})
    curr_cf = cf.get(latest_p, {})
    curr_rt = rt.get(latest_p, {})

    pat = curr_pl.get('Net Profit')
    sales = curr_pl.get('Sales') or curr_pl.get('Revenue')
    prev_sales = prev3_pl.get('Sales') or prev3_pl.get('Revenue')
    opm = curr_pl.get('OPM %') or curr_pl.get('Financing Margin %')
    prev_opm = prev3_pl.get('OPM %') or prev3_pl.get('Financing Margin %')
    cfo = curr_cf.get('Cash from Operating Activity')

    roce = ratios.get('ROCE', curr_rt.get('ROCE %', np.nan))
    pe = ratios.get('Stock P/E', np.nan)
    wc_days = curr_rt.get('Working Capital Days', np.nan)

    eq = curr_bs.get('Equity Capital') or 0
    res = curr_bs.get('Reserves') or 0
    nw = eq + res
    borrowings = curr_bs.get('Borrowings') or 0
    if nw <= 0:
        return None  # Ignore distressed companies with negative net worth
    de = borrowings / nw

    if cfo is None or pat is None or pat <= 0:
        cfo_pat = 0.0
    else:
        cfo_pat = min(3.0, max(0.0, cfo / pat))

    if pe is None or pd.isna(pe) or pe <= 0:
        return None  # Ignore stocks with missing or negative P/E

    if roce is None or pd.isna(roce):
        return None  # Ignore stocks with missing ROCE

    sales_g = compound.get('Compounded Sales Growth_3 Years')
    if sales_g is None and sales and prev_sales and sales > 0 and prev_sales > 0:
        sales_g = ((sales / prev_sales) ** (1/3) - 1) * 100
    if sales_g is None or pd.isna(sales_g):
        return None  # Ignore stocks with missing sales growth history

    opm_exp = (opm - prev_opm) if (opm is not None and prev_opm is not None) else 0.0

    meta = meta_dict.get(symbol, {})
    return {
        'symbol': symbol,
        'name': meta.get('Company Name', symbol),
        'industry': meta.get('Industry', 'Unknown'),
        'benchmark': meta.get('Benchmark_Index', 'Unknown'),
        'roce': roce,
        'pe_ratio': pe,
        'hist_sales_cagr': sales_g,
        'opm_expansion_3y': opm_exp,
        'debt_to_equity': de,
        'cfo_to_pat': cfo_pat,
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

def build_portfolio(K, max_per_sector, min_w, max_w, max_sec_w, scored_df):
    selected = []
    ind_counts = {}
    for _, row in scored_df.iterrows():
        ind = row['industry']
        if ind_counts.get(ind, 0) < max_per_sector:
            selected.append(row)
            ind_counts[ind] = ind_counts.get(ind, 0) + 1
        if len(selected) == K:
            break

    df_k = pd.DataFrame(selected).reset_index(drop=True)

    # Covariance
    price_dict = {}
    for sym in df_k['symbol']:
        s = get_stock_series(sym)
        if s is not None and len(s) > 15:
            price_dict[sym] = s

    prices_df = pd.DataFrame(price_dict).pct_change().dropna(how='all')
    cov = prices_df.cov() * 252.0
    cov = cov.fillna(cov.median().median() if not cov.empty else 0.04)

    valid_syms = list(df_k['symbol'])
    N = len(valid_syms)

    comp_scores = df_k['composite_score'].values
    min_sc, max_sc = comp_scores.min(), comp_scores.max()
    norm_sc = (comp_scores - min_sc) / (max_sc - min_sc + 1e-6)
    expected_returns = 0.15 + norm_sc * 0.10

    cov_arr = cov.loc[valid_syms, valid_syms].values
    vols = np.sqrt(np.diag(cov_arr))

    rf = 0.07
    init_w = np.ones(N) / N
    bounds = tuple((min_w, max_w) for _ in range(N))
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

    industries = df_k['industry'].values
    for ind in np.unique(industries):
        mask = (industries == ind).astype(float)
        constraints.append({
            'type': 'ineq',
            'fun': lambda w, m=mask: max_sec_w - np.dot(w, m)
        })

    def neg_sharpe(w):
        p_ret = np.dot(w, expected_returns)
        p_vol = np.sqrt(np.dot(w.T, np.dot(cov_arr, w)))
        return -(p_ret - rf) / p_vol if p_vol > 0 else 0.0

    res = minimize(neg_sharpe, init_w, method='SLSQP', bounds=bounds, constraints=constraints)
    if res.success:
        opt_w = np.clip(res.x, min_w, max_w)
        opt_w /= np.sum(opt_w)
    else:
        opt_w = init_w

    df_k['optimal_weight_pct'] = np.round(opt_w * 100.0, 2)
    diff = round(100.0 - float(df_k['optimal_weight_pct'].sum()), 2)
    if abs(diff) > 0:
        df_k.loc[0, 'optimal_weight_pct'] += diff

    df_k['equal_weight_pct'] = round(100.0 / K, 2)
    diff_ew = round(100.0 - float(df_k['equal_weight_pct'].sum()), 2)
    if abs(diff_ew) > 0:
        df_k.loc[0, 'equal_weight_pct'] += diff_ew

    CAP_10L = 1_000_000.0
    CAP_1CR = 10_000_000.0

    df_k['invest_10L_opt'] = np.round((df_k['optimal_weight_pct'] / 100.0) * CAP_10L, 0)
    df_k['invest_1CR_opt'] = np.round((df_k['optimal_weight_pct'] / 100.0) * CAP_1CR, 0)
    df_k['invest_10L_ew'] = np.round((df_k['equal_weight_pct'] / 100.0) * CAP_10L, 0)
    df_k['invest_1CR_ew'] = np.round((df_k['equal_weight_pct'] / 100.0) * CAP_1CR, 0)

    p_ret = float(np.dot(opt_w, expected_returns))
    p_vol = float(np.sqrt(np.dot(opt_w.T, np.dot(cov_arr, opt_w))))
    p_sharpe = float((p_ret - rf) / p_vol)

    return df_k, {
        'expected_return': p_ret,
        'volatility': p_vol,
        'sharpe': p_sharpe,
        'weighted_roce': float(np.dot(opt_w, df_k['roce'])),
        'weighted_de': float(np.dot(opt_w, df_k['debt_to_equity'])),
        'weighted_cfo_pat': float(np.dot(opt_w, df_k['cfo_to_pat'])),
        'num_sectors': df_k['industry'].nunique()
    }

def main():
    u_df = pd.read_csv(UNIVERSE_CSV)
    meta_dict = u_df.set_index('Symbol').to_dict(orient='index')
    valid_symbols = [s for s in u_df['Symbol'] if has_sufficient_history(s)]

    parsed = []
    for s in valid_symbols:
        d = parse_latest_fundamentals(s, meta_dict)
        if d: parsed.append(d)

    df = pd.DataFrame(parsed)

    df['cfo_to_pat'] = df['cfo_to_pat'].clip(0.0, 2.5)
    df['hist_sales_cagr'] = df['hist_sales_cagr'].fillna(df['hist_sales_cagr'].median()).clip(-10.0, 60.0)
    df['roce'] = df['roce'].fillna(df['roce'].median()).clip(5.0, 75.0)
    df['opm_expansion_3y'] = df['opm_expansion_3y'].fillna(0.0).clip(-20.0, 30.0)
    df['debt_to_equity'] = df['debt_to_equity'].fillna(0.0).clip(0.0, 3.0)
    df['wc_days'] = df['wc_days'].fillna(df['wc_days'].median()).clip(-50.0, 180.0)
    df['pe_ratio'] = df['pe_ratio'].fillna(df['pe_ratio'].median()).clip(5.0, 150.0)

    for c in ['roce', 'hist_sales_cagr', 'opm_expansion_3y', 'debt_to_equity', 'cfo_to_pat', 'wc_days']:
        mean_c, std_c = df[c].mean(), df[c].std()
        df[f'{c}_z'] = (df[c] - mean_c) / std_c if std_c > 0 else 0.0

    score = (
        NEXT50_WEIGHTS['cfo_to_pat'] * df['cfo_to_pat_z']
        + NEXT50_WEIGHTS['roce'] * df['roce_z']
        + NEXT50_WEIGHTS['hist_sales_cagr'] * df['hist_sales_cagr_z']
        + NEXT50_WEIGHTS['debt_to_equity'] * df['debt_to_equity_z']
        + NEXT50_WEIGHTS['opm_expansion_3y'] * df['opm_expansion_3y_z']
        + NEXT50_WEIGHTS['wc_days'] * df['wc_days_z']
    )

    pe_penalty = np.where(df['pe_ratio'] > 75, (df['pe_ratio'] - 75) / 100.0, 0.0)
    df['composite_score'] = score - 0.15 * pe_penalty

    df_sorted = df.sort_values('composite_score', ascending=False).reset_index(drop=True)

    # 1. BEST 10 STOCKS PORTFOLIO
    # Max 2 per sector, bounds: 5.0% to 15.0%, max 25% per sector
    df_10, stats_10 = build_portfolio(K=10, max_per_sector=2, min_w=0.05, max_w=0.15, max_sec_w=0.25, scored_df=df_sorted)

    # 2. BEST 30 STOCKS PORTFOLIO
    # Max 4 per sector, bounds: 1.5% to 6.0%, max 20% per sector
    df_30, stats_30 = build_portfolio(K=30, max_per_sector=4, min_w=0.015, max_w=0.060, max_sec_w=0.20, scored_df=df_sorted)

    print("="*90)
    print("BEST 10 STOCKS PORTFOLIO (NIFTY NEXT 50 MODEL)")
    print("="*90)
    cols = ['symbol', 'name', 'benchmark', 'industry', 'roce', 'hist_sales_cagr', 'debt_to_equity', 'cfo_to_pat', 'pe_ratio', 'optimal_weight_pct', 'invest_10L_opt', 'invest_1CR_opt']
    pd.set_option('display.max_columns', 15)
    pd.set_option('display.width', 1000)
    print(df_10[cols].to_string(index=False))
    print(f"\n10-Stock Stats: ROCE={stats_10['weighted_roce']:.1f}%, D/E={stats_10['weighted_de']:.2f}, CFO/PAT={stats_10['weighted_cfo_pat']:.2f}x, Sharpe={stats_10['sharpe']:.2f}, Sectors={stats_10['num_sectors']}")

    print("\n" + "="*90)
    print("BEST 30 STOCKS PORTFOLIO (NIFTY NEXT 50 MODEL)")
    print("="*90)
    print(df_30[cols].to_string(index=False))
    print(f"\n30-Stock Stats: ROCE={stats_30['weighted_roce']:.1f}%, D/E={stats_30['weighted_de']:.2f}, CFO/PAT={stats_30['weighted_cfo_pat']:.2f}x, Sharpe={stats_30['sharpe']:.2f}, Sectors={stats_30['num_sectors']}")

    # Save exports
    os.makedirs("/Users/viralmehta/investment/output", exist_ok=True)
    df_10.to_csv("/Users/viralmehta/investment/output/nifty250_top10_stocks.csv", index=False)
    df_30.to_csv("/Users/viralmehta/investment/output/nifty250_top30_stocks.csv", index=False)
    if 'OUTPUT_DIR' in locals() and os.path.exists(OUTPUT_DIR):
        df_10.to_csv(os.path.join(OUTPUT_DIR, "nifty250_top10_stocks.csv"), index=False)
        df_30.to_csv(os.path.join(OUTPUT_DIR, "nifty250_top30_stocks.csv"), index=False)
    if 'DATA_DIR' in locals() and os.path.exists(DATA_DIR):
        df_10.to_csv(os.path.join(DATA_DIR, "nifty250_top10_stocks.csv"), index=False)
        df_30.to_csv(os.path.join(DATA_DIR, "nifty250_top30_stocks.csv"), index=False)
    print("\nSaved output CSVs.")

if __name__ == '__main__':
    main()
