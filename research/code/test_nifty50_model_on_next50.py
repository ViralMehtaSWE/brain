#!/usr/bin/env python3
"""
Test Transferability: Apply NIFTY 50 Weights & Features to the NIFTY NEXT 50 Universe
Evaluates whether the large-cap quality/cash-flow heavy model outperforms the Nifty Next 50 benchmark.
"""

import os
import sys
import re
import json
import urllib.request
import numpy as np
import pandas as pd
from scipy.optimize import minimize

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

# 1. Official Nifty Next 50 Benchmark performance over last 3 years
BENCHMARK_CAGR = 0.1662      # 16.62%
BENCHMARK_VOL = 0.1883       # 18.83%
BENCHMARK_SHARPE = (BENCHMARK_CAGR - 0.07) / BENCHMARK_VOL  # 0.511

# 2. NIFTY 50 Weights (Large Cap Calibrated Weights)
# Quality & Cash conversion heavy:
NIFTY_50_WEIGHTS = {
    'roce': 0.25,
    'hist_sales_cagr_3y': 0.20,
    'cfo_to_pat': 0.15,
    'opm': 0.15,
    'debt_to_equity': 0.15,  # Penalty
    'pe_ratio': 0.10         # Penalty
}

# Also test unrounded regression weights derived from Nifty 50 panel
NIFTY_50_UNROUNDED = {
    'cfo_to_pat': 0.3524,
    'roce': 0.2481,
    'debt_to_equity': 0.1560,
    'opm': 0.1245,
    'hist_sales_cagr_3y': 0.1190
}

# 3. For comparison: Nifty Next 50 Native Weights (Growth & Momentum heavy)
NEXT_50_NATIVE_WEIGHTS = {
    'hist_sales_cagr_3y': 0.35,
    'opm_expansion_3y': 0.20,
    'roce': 0.20,
    'debt_to_equity': 0.15,
    'cfo_to_pat': 0.10
}

def clean_num(val_str):
    if val_str is None: return np.nan
    s = str(val_str).replace('%', '').replace(',', '').strip()
    if s in ['', '-', 'None', 'N/A']: return np.nan
    try: return float(s)
    except: return np.nan

def parse_stock_file(ticker):
    t_clean = 'TATAMOTORS' if ticker == 'TMPV' else ticker.upper().strip()
    fpath = os.path.join(CACHE_DIR, f"{t_clean}.html")
    if not os.path.exists(fpath): return None

    with open(fpath, "r", encoding="utf-8") as f:
        html = f.read()
    if len(html) < 5000: return None

    cid_m = re.search(r'data-row-company-id=\"(\d+)\"', html) or re.search(r'/api/company/(\d+)/', html)
    cid = cid_m.group(1) if cid_m else None

    # Ratios
    ratios = {}
    for m in re.finditer(r'<span class=\"name\">\s*([^<]+?)\s*</span>\s*<span class=\"nowrap value\">\s*₹?\s*<span class=\"number\">([^<]+)</span>', html):
        ratios[m.group(1).strip()] = clean_num(m.group(2))

    # Compound table
    compound = {}
    for m in re.finditer(r'<table[^>]+class=\"ranges-table\"[^>]*>(.*?)</table>', html, re.DOTALL):
        th = re.search(r'<th[^>]*>(.*?)</th>', m.group(1), re.DOTALL)
        if th:
            title = re.sub(r'<[^>]+>', '', th.group(1)).strip()
            for term, val in re.findall(r'<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>', m.group(1), re.DOTALL):
                compound[f"{title}_{term.replace(':', '').strip()}"] = clean_num(val)

    def parse_last(sec_id):
        pos = html.find(f'id="{sec_id}"')
        if pos == -1: return {}
        sec = html[pos:html.find('</section>', pos)]
        tbody = re.search(r'<tbody>(.*?)</tbody>', sec, re.DOTALL)
        res = {}
        if tbody:
            for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', tbody.group(1), re.DOTALL):
                tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
                clean_tds = [clean_num(re.sub(r'<[^>]+>', '', td)) for td in tds]
                if len(clean_tds) > 1:
                    name = ' '.join(re.sub(r'<[^>]+>', '', tds[0]).replace('&nbsp;', ' ').replace('+', '').split())
                    vals = [v for v in clean_tds[1:] if pd.notnull(v)]
                    res[name] = vals[-1] if vals else np.nan
        return res

    pl = parse_last('profit-loss')
    bs = parse_last('balance-sheet')
    cf = parse_last('cash-flow')
    rt = parse_last('ratios')

    pat = pl.get('Net Profit', np.nan)
    cfo = cf.get('Cash from Operating Activity', np.nan)
    eq = bs.get('Equity Capital', 0) or 0
    res = bs.get('Reserves', 0) or 0
    nw = eq + res
    borrowings = bs.get('Borrowings', 0) or 0

    sales_g = compound.get('Compounded Sales Growth_3 Years', np.nan)
    roce = ratios.get('ROCE', rt.get('ROCE %', np.nan))
    pe = ratios.get('Stock P/E', np.nan)
    opm = pl.get('OPM %', pl.get('Financing Margin %', np.nan))
    de = (borrowings / nw) if nw > 0 else 0.0
    cfo_pat = (cfo / pat) if (cfo is not None and pat and pat > 0) else 1.0

    return {
        'Symbol': ticker,
        'company_id': cid,
        'roce': roce,
        'hist_sales_cagr_3y': sales_g,
        'opm': opm,
        'debt_to_equity': de,
        'cfo_to_pat': cfo_pat,
        'pe_ratio': pe
    }

def get_actual_prices(ticker, cid):
    t_clean = 'TATAMOTORS' if ticker == 'TMPV' else ticker.upper().strip()
    cache = os.path.join(CACHE_DIR, f"{t_clean}_price.csv")
    if os.path.exists(cache):
        df = pd.read_csv(cache, parse_dates=['date'])
        df = df.dropna().drop_duplicates('date').sort_values('date')
        if len(df) > 30:
            return df.set_index('date')['price']

    if not cid: return None
    url = f"https://www.screener.in/api/company/{cid}/chart/?q=Price-DMA50-DMA200-Volume&days=1095"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for ds in data.get('datasets', []):
                if ds.get('metric') == 'Price':
                    df = pd.DataFrame(ds['values'], columns=['date', 'price'])
                    df['price'] = pd.to_numeric(df['price'], errors='coerce')
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.dropna().drop_duplicates('date').sort_values('date')
                    df.to_csv(cache, index=False)
                    return df.set_index('date')['price']
    except Exception:
        pass
    return None

def run_experiment():
    df_250 = pd.read_csv(os.path.join(SCRATCH_DIR, "nifty_250_universe.csv"))
    next50_constituents = df_250[df_250['Benchmark_Index'] == 'NIFTY NEXT 50'].copy()

    parsed = []
    for _, row in next50_constituents.iterrows():
        sym = row['Symbol']
        d = parse_stock_file(sym)
        if d:
            d['Company_Name'] = row['Company Name']
            d['Industry'] = row['Industry']
            parsed.append(d)

    df = pd.DataFrame(parsed)
    print(f"Successfully loaded and parsed {len(df)} NIFTY NEXT 50 stocks.")

    # Clean / winsorize
    for c in ['roce', 'hist_sales_cagr_3y', 'opm', 'debt_to_equity', 'cfo_to_pat']:
        df[c] = df[c].fillna(df[c].median()).clip(df[c].quantile(0.02), df[c].quantile(0.98))
    df['pe_ratio'] = df['pe_ratio'].fillna(df['pe_ratio'].median()).clip(5.0, 150.0)

    # Standardize across the Next 50 universe
    for c in ['roce', 'hist_sales_cagr_3y', 'opm', 'debt_to_equity', 'cfo_to_pat', 'pe_ratio']:
        mean_c = df[c].mean()
        std_c = df[c].std()
        df[f'{c}_z'] = (df[c] - mean_c) / std_c if std_c > 0 else 0.0

    # Apply NIFTY 50 Weights
    df['nifty50_model_score'] = (
        NIFTY_50_WEIGHTS['roce'] * df['roce_z']
        + NIFTY_50_WEIGHTS['hist_sales_cagr_3y'] * df['hist_sales_cagr_3y_z']
        + NIFTY_50_WEIGHTS['cfo_to_pat'] * df['cfo_to_pat_z']
        + NIFTY_50_WEIGHTS['opm'] * df['opm_z']
        - NIFTY_50_WEIGHTS['debt_to_equity'] * df['debt_to_equity_z']
        - NIFTY_50_WEIGHTS['pe_ratio'] * df['pe_ratio_z']
    )

    # Apply Nifty Next 50 Native Weights for comparison
    df['next50_native_score'] = (
        NEXT_50_NATIVE_WEIGHTS['hist_sales_cagr_3y'] * df['hist_sales_cagr_3y_z']
        + NEXT_50_NATIVE_WEIGHTS['roce'] * df['roce_z']
        + NEXT_50_NATIVE_WEIGHTS['opm_expansion_3y'] * df['opm_z']
        + NEXT_50_NATIVE_WEIGHTS['cfo_to_pat'] * df['cfo_to_pat_z']
        - NEXT_50_NATIVE_WEIGHTS['debt_to_equity'] * df['debt_to_equity_z']
    )

    # Select top 20 stocks for both
    top20_transferred = df.sort_values('nifty50_model_score', ascending=False).head(20).copy()
    top20_native = df.sort_values('next50_native_score', ascending=False).head(20).copy()

    # Load price histories for top 20 transferred
    price_dict_transferred = {}
    for _, r in top20_transferred.iterrows():
        p = get_actual_prices(r['Symbol'], r['company_id'])
        if p is not None and len(p) > 30:
            price_dict_transferred[r['Symbol']] = p

    prices_transferred = pd.DataFrame(price_dict_transferred).dropna(how='all').ffill().dropna()
    prices_transferred.index = pd.to_datetime(prices_transferred.index)
    prices_transferred = prices_transferred.sort_index()
    daily_ret_trans = prices_transferred.pct_change().dropna()
    
    # 3-year Realized Performance of Transferred Model
    ann_factor = 252.0
    mu_trans = daily_ret_trans.mean() * ann_factor
    cov_trans = daily_ret_trans.cov() * ann_factor

    N_trans = len(daily_ret_trans.columns)
    rf_rate = 0.07

    def neg_sharpe_trans(w):
        p_ret = np.dot(w, mu_trans)
        p_vol = np.sqrt(np.dot(w.T, np.dot(cov_trans, w)))
        return -(p_ret - rf_rate) / p_vol if p_vol > 0 else 0.0

    init_w = np.ones(N_trans) / N_trans
    bounds = tuple((0.025, 0.10) for _ in range(N_trans))
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
    res_trans = minimize(neg_sharpe_trans, init_w, method='SLSQP', bounds=bounds, constraints=constraints)

    w_opt_trans = res_trans.x if res_trans.success else init_w
    port_ret_trans = float(np.dot(w_opt_trans, mu_trans))
    port_vol_trans = float(np.sqrt(np.dot(w_opt_trans.T, np.dot(cov_trans, w_opt_trans))))
    sharpe_trans = float((port_ret_trans - rf_rate) / port_vol_trans)

    # Calculate each stock's full 3Y CAGR from its individual price series
    stock_3y_cagr = {}
    for sym in top20_transferred['Symbol']:
        cache = os.path.join(CACHE_DIR, f"{sym}_price.csv")
        if os.path.exists(cache):
            df_p = pd.read_csv(cache, parse_dates=['date']).sort_values('date')
            if len(df_p) > 30:
                first_val = df_p['price'].iloc[0]
                last_val = df_p['price'].iloc[-1]
                days = (df_p['date'].iloc[-1] - df_p['date'].iloc[0]).days
                years = days / 365.25
                if years >= 0.8 and first_val > 0:
                    stock_3y_cagr[sym] = ((last_val / first_val) ** (1.0 / years) - 1.0) * 100

    valid_cagrs = list(stock_3y_cagr.values())
    eq_ret_trans = np.mean(valid_cagrs) if valid_cagrs else 0.0

    # Build detailed output table
    weights_list = []
    for i, (_, row) in enumerate(top20_transferred.iterrows()):
        sym = row['Symbol']
        if sym in daily_ret_trans.columns:
            col_idx = list(daily_ret_trans.columns).index(sym)
            weights_list.append(round(w_opt_trans[col_idx] * 100, 2))
        else:
            weights_list.append(5.0)
    top20_transferred['weight_pct'] = weights_list
    top20_transferred['3Y_CAGR_pct'] = [round(stock_3y_cagr.get(s, np.nan), 2) for s in top20_transferred['Symbol']]

    print("\n" + "="*85)
    print("TOP 20 NIFTY NEXT 50 STOCKS SELECTED BY NIFTY 50 WEIGHTS & FEATURES")
    print("="*85)
    cols_show = ['Symbol', 'Company_Name', 'Industry', 'weight_pct', 'roce', 'hist_sales_cagr_3y', 'cfo_to_pat', 'pe_ratio', '3Y_CAGR_pct']
    print(top20_transferred[cols_show].to_string(index=False))

    print("\n" + "="*85)
    print("BENCHMARK OUTPERFORMANCE EVALUATION (NIFTY 50 WEIGHTS APPLIED TO NEXT 50)")
    print("="*85)
    print(f"{'Metric':<30} | {'Transferred N50 Model':<22} | {'Nifty Next 50 Benchmark':<24} | {'Active Outperformance':<20}")
    print("-" * 105)
    cagr_diff = (port_ret_trans - BENCHMARK_CAGR) * 100
    vol_diff = (port_vol_trans - BENCHMARK_VOL) * 100
    sharpe_diff = sharpe_trans - BENCHMARK_SHARPE
    print(f"{'Realized 3Y Annualized CAGR':<30} | {port_ret_trans*100:>20.2f}% | {BENCHMARK_CAGR*100:>22.2f}% | {cagr_diff:>+18.2f}%")
    print(f"{'Equal-Weighted 20-Stock CAGR':<30} | {eq_ret_trans:>20.2f}% | {BENCHMARK_CAGR*100:>22.2f}% | {(eq_ret_trans - BENCHMARK_CAGR*100):>+18.2f}%")
    print(f"{'Annualized Volatility':<30} | {port_vol_trans*100:>20.2f}% | {BENCHMARK_VOL*100:>22.2f}% | {vol_diff:>+18.2f}%")
    print(f"{'Sharpe Ratio (Rf=7.0%)':<30} | {sharpe_trans:>22.2f} | {BENCHMARK_SHARPE:>24.2f} | {sharpe_diff:>+20.2f}")

    # Overlap analysis: how many stocks overlap between Nifty 50 model vs Native Next 50 model?
    overlap = set(top20_transferred['Symbol']).intersection(set(top20_native['Symbol']))
    print("\n" + "="*85)
    print(f"Overlap between Nifty 50 Model and Native Next 50 Model: {len(overlap)} / 20 stocks")
    print(f"Common Stocks: {sorted(list(overlap))}")
    print("="*85)

    results = {
        'port_ret': port_ret_trans,
        'eq_ret': eq_ret_trans,
        'port_vol': port_vol_trans,
        'sharpe': sharpe_trans,
        'benchmark_cagr': BENCHMARK_CAGR,
        'benchmark_vol': BENCHMARK_VOL,
        'benchmark_sharpe': BENCHMARK_SHARPE,
        'active_cagr': port_ret_trans - BENCHMARK_CAGR,
        'active_sharpe': sharpe_trans - BENCHMARK_SHARPE,
        'top20': top20_transferred[cols_show].to_dict(orient='records'),
        'overlap_count': len(overlap),
        'overlap_stocks': sorted(list(overlap))
    }
    with open(os.path.join(SCRATCH_DIR, "nifty50_on_next50_results.json"), "w") as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    run_experiment()
