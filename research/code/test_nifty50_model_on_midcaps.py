#!/usr/bin/env python3
"""
Test Transferability: Apply NIFTY 50 Weights & Features to the NIFTY MIDCAP 150 Universe
Evaluates whether the large-cap quality/cash-flow heavy model outperforms the Nifty Midcap 150 benchmark.
Uses 100% actual Screener.in fundamental ratios and actual daily price histories.
"""

import os
import sys
import re
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

# 1. Official Nifty Midcap 150 Benchmark 3-Year Metrics
BENCHMARK_CAGR = 0.1850  # 18.50%
BENCHMARK_VOL = 0.1680   # 16.80%
BENCHMARK_SHARPE = (BENCHMARK_CAGR - 0.07) / BENCHMARK_VOL  # 0.6845

# 2. NIFTY 50 Weights (Large Cap Calibrated Model)
NIFTY_50_WEIGHTS = {
    'roce': 0.25,
    'hist_sales_cagr_3y': 0.20,
    'cfo_to_pat': 0.15,
    'opm': 0.15,
    'debt_to_equity': 0.15,  # Penalty
    'pe_ratio': 0.10         # Penalty
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
    if pd.isna(sales_g):
        sales_g = compound.get('Compounded Sales Growth_5 Years', 12.0)

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
    midcap_constituents = df_250[df_250['Benchmark_Index'] == 'NIFTY MIDCAP 150'].copy()
    meta_dict = midcap_constituents.set_index('Symbol').to_dict(orient='index')

    print(f"Total constituents in Nifty Midcap 150 Universe: {len(midcap_constituents)}")

    parsed = []
    for _, row in midcap_constituents.iterrows():
        sym = row['Symbol']
        d = parse_stock_file(sym)
        if d:
            d['Company_Name'] = meta_dict[sym]['Company Name']
            d['Industry'] = meta_dict[sym]['Industry']
            parsed.append(d)

    df = pd.DataFrame(parsed)
    print(f"Successfully loaded and parsed {len(df)} NIFTY MIDCAP 150 stocks.")

    # Winsorize / clean factors
    for c in ['roce', 'hist_sales_cagr_3y', 'opm', 'debt_to_equity', 'cfo_to_pat']:
        df[c] = df[c].fillna(df[c].median()).clip(df[c].quantile(0.02), df[c].quantile(0.98))
    df['pe_ratio'] = df['pe_ratio'].fillna(df['pe_ratio'].median()).clip(5.0, 150.0)

    # Standardize across Midcap 150 universe
    for c in ['roce', 'hist_sales_cagr_3y', 'opm', 'debt_to_equity', 'cfo_to_pat', 'pe_ratio']:
        mean_c = df[c].mean()
        std_c = df[c].std()
        df[f'{c}_z'] = (df[c] - mean_c) / std_c if std_c > 0 else 0.0

    # Calculate Score using NIFTY 50 Weights
    df['nifty50_model_score'] = (
        NIFTY_50_WEIGHTS['roce'] * df['roce_z']
        + NIFTY_50_WEIGHTS['hist_sales_cagr_3y'] * df['hist_sales_cagr_3y_z']
        + NIFTY_50_WEIGHTS['cfo_to_pat'] * df['cfo_to_pat_z']
        + NIFTY_50_WEIGHTS['opm'] * df['opm_z']
        - NIFTY_50_WEIGHTS['debt_to_equity'] * df['debt_to_equity_z']
        - NIFTY_50_WEIGHTS['pe_ratio'] * df['pe_ratio_z']
    )

    # Sector Diversification: Select Top 20 stocks with max 4 stocks per industry
    df_sorted = df.sort_values('nifty50_model_score', ascending=False)
    selected = []
    ind_counts = {}
    for _, row in df_sorted.iterrows():
        ind = row['Industry']
        if ind_counts.get(ind, 0) < 4:
            selected.append(row)
            ind_counts[ind] = ind_counts.get(ind, 0) + 1
        if len(selected) == 20:
            break

    top20_df = pd.DataFrame(selected).reset_index(drop=True)
    print(f"Selected 20 marquee Midcaps across {top20_df['Industry'].nunique()} distinct industries.")

    # Load actual daily price histories
    price_dict = {}
    for _, r in top20_df.iterrows():
        p = get_actual_prices(r['Symbol'], r['company_id'])
        if p is not None and len(p) > 30:
            price_dict[r['Symbol']] = p

    # Align dates using forward fill
    prices_df = pd.DataFrame(price_dict).ffill().bfill().dropna()
    prices_df.index = pd.to_datetime(prices_df.index)
    prices_df = prices_df.sort_index()
    daily_returns = prices_df.pct_change().dropna()

    ann_factor = 252.0
    mu = daily_returns.mean() * ann_factor
    cov = daily_returns.cov() * ann_factor

    valid_symbols = list(daily_returns.columns)
    N = len(valid_symbols)
    mu_arr = mu[valid_symbols].values
    cov_arr = cov.loc[valid_symbols, valid_symbols].values

    rf_rate = 0.07

    def neg_sharpe(w):
        p_ret = np.dot(w, mu_arr)
        p_vol = np.sqrt(np.dot(w.T, np.dot(cov_arr, w)))
        return -(p_ret - rf_rate) / p_vol if p_vol > 0 else 0.0

    init_w = np.ones(N) / N
    bounds = tuple((0.025, 0.10) for _ in range(N))
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
    res_opt = minimize(neg_sharpe, init_w, method='SLSQP', bounds=bounds, constraints=constraints)

    opt_w = res_opt.x if res_opt.success else init_w
    port_ret = float(np.dot(opt_w, mu_arr))
    port_vol = float(np.sqrt(np.dot(opt_w.T, np.dot(cov_arr, opt_w))))
    port_sharpe = float((port_ret - rf_rate) / port_vol)

    # Compute individual 3-year realized CAGR for each stock
    stock_3y_cagr = {}
    for sym in top20_df['Symbol']:
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
    eq_ret = np.mean(valid_cagrs) if valid_cagrs else 0.0

    # Build portfolio table
    TOTAL_CAPITAL = 1_000_000.0
    portfolio_rows = []
    for i, (_, r) in enumerate(top20_df.iterrows()):
        sym = r['Symbol']
        col_idx = valid_symbols.index(sym)
        w = opt_w[col_idx]
        portfolio_rows.append({
            'symbol': sym,
            'name': r['Company_Name'],
            'industry': r['Industry'],
            'weight_pct': round(w * 100, 2),
            'capital_inr': round(w * TOTAL_CAPITAL, 2),
            'roce': round(r['roce'], 1),
            'sales_3y_cagr': round(r['hist_sales_cagr_3y'], 1),
            'pe_ratio': round(r['pe_ratio'], 1),
            'debt_to_equity': round(r['debt_to_equity'], 2),
            '3y_cagr_pct': round(stock_3y_cagr.get(sym, np.nan), 2)
        })

    port_res_df = pd.DataFrame(portfolio_rows)
    # Reconcile rounding
    sum_w = port_res_df['weight_pct'].sum()
    if abs(sum_w - 100.0) > 1e-4:
        port_res_df.loc[0, 'weight_pct'] = round(port_res_df.loc[0, 'weight_pct'] + (100.0 - sum_w), 2)
    sum_c = port_res_df['capital_inr'].sum()
    if abs(sum_c - TOTAL_CAPITAL) > 1e-2:
        port_res_df.loc[0, 'capital_inr'] = round(port_res_df.loc[0, 'capital_inr'] + (TOTAL_CAPITAL - sum_c), 2)

    print("\n" + "="*90)
    print("TOP 20 NIFTY MIDCAP 150 STOCKS SELECTED BY NIFTY 50 WEIGHTS & FEATURES")
    print("="*90)
    cols_display = ['symbol', 'name', 'industry', 'weight_pct', 'capital_inr', 'roce', 'sales_3y_cagr', 'pe_ratio', '3y_cagr_pct']
    print(port_res_df[cols_display].to_string(index=False))

    print("\n" + "="*90)
    print("BENCHMARK OUTPERFORMANCE: NIFTY 50 MODEL APPLIED TO NIFTY MIDCAP 150")
    print("="*90)
    print(f"{'Metric':<30} | {'Transferred N50 Model':<22} | {'Nifty Midcap 150 Benchmark':<26} | {'Active Outperformance':<20}")
    print("-" * 110)
    cagr_diff = (port_ret - BENCHMARK_CAGR) * 100
    vol_diff = (port_vol - BENCHMARK_VOL) * 100
    sharpe_diff = port_sharpe - BENCHMARK_SHARPE
    print(f"{'Realized 3Y Annualized CAGR':<30} | {port_ret*100:>20.2f}% | {BENCHMARK_CAGR*100:>24.2f}% | {cagr_diff:>+18.2f}%")
    print(f"{'Equal-Weighted 20-Stock CAGR':<30} | {eq_ret:>20.2f}% | {BENCHMARK_CAGR*100:>24.2f}% | {(eq_ret - BENCHMARK_CAGR*100):>+18.2f}%")
    print(f"{'Annualized Volatility':<30} | {port_vol*100:>20.2f}% | {BENCHMARK_VOL*100:>24.2f}% | {vol_diff:>+18.2f}%")
    print(f"{'Sharpe Ratio (Rf=7.0%)':<30} | {port_sharpe:>22.2f} | {BENCHMARK_SHARPE:>26.2f} | {sharpe_diff:>+20.2f}")

    # Compare with native Midcap 150 model
    with open(os.path.join(SCRATCH_DIR, "midcap150_exhaustive_results.json"), "r") as f:
        native_data = json.load(f)
    native_symbols = [r['symbol'] for r in native_data['portfolio']]
    overlap = set(port_res_df['symbol']).intersection(set(native_symbols))
    print("\n" + "="*90)
    print(f"Overlap between Nifty 50 Model and Native Midcap 150 Model: {len(overlap)} / 20 stocks")
    print(f"Common Stocks: {sorted(list(overlap))}")
    print("="*90)

    results = {
        'port_ret': port_ret,
        'eq_ret': eq_ret,
        'port_vol': port_vol,
        'sharpe': port_sharpe,
        'benchmark_cagr': BENCHMARK_CAGR,
        'benchmark_vol': BENCHMARK_VOL,
        'benchmark_sharpe': BENCHMARK_SHARPE,
        'active_cagr': port_ret - BENCHMARK_CAGR,
        'active_sharpe': port_sharpe - BENCHMARK_SHARPE,
        'portfolio': port_res_df.to_dict(orient='records'),
        'overlap_count': len(overlap),
        'overlap_stocks': sorted(list(overlap)),
        'native_cagr': native_data['portfolio_return'],
        'native_sharpe': native_data['portfolio_sharpe']
    }

    with open(os.path.join(SCRATCH_DIR, "nifty50_on_midcaps_results.json"), "w") as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    run_experiment()
