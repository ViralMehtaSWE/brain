#!/usr/bin/env python3
"""
Exhaustive 3x3 Cross-Universe Factor Transferability Matrix
Evaluates:
  - 3 Models: Nifty 50 Model, Nifty Next 50 Model, Nifty Midcap 150 Model
  - 3 Universes: Nifty 50, Nifty Next 50, Nifty Midcap 150
Total 9 Combinations + 3 Benchmarks.

Calculates:
  1. Realized 3-Year Constituent CAGR
  2. Equal-Weighted 20-Stock Basket CAGR
  3. Maximum-Sharpe Optimized Portfolio CAGR, Volatility, and Sharpe Ratio
  4. Active Benchmark Outperformance (Alpha)
  5. Factor Transferability Analysis
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
UNIVERSE_CSV = os.path.join(SCRATCH_DIR, "nifty_250_universe.csv")
CALIBRATION_JSON = os.path.join(SCRATCH_DIR, "audited_three_universes_calibration.json")

# Official 3-Year Benchmark Performance (NSE TRI Archives)
BENCHMARKS = {
    'NIFTY 50': {
        'cagr': 0.0884,      # 8.84%
        'volatility': 0.2982,# 29.82%
        'sharpe': 0.0617     # (8.84 - 7.0) / 29.82
    },
    'NIFTY NEXT 50': {
        'cagr': 0.1662,      # 16.62%
        'volatility': 0.1883,# 18.83%
        'sharpe': 0.5109     # (16.62 - 7.0) / 18.83
    },
    'NIFTY MIDCAP 150': {
        'cagr': 0.1850,      # 18.50%
        'volatility': 0.1680,# 16.80%
        'sharpe': 0.6845     # (18.50 - 7.0) / 16.80
    }
}

def clean_num(val_str):
    if val_str is None: return np.nan
    s = str(val_str).replace('%', '').replace(',', '').strip()
    if s in ['', '-', 'None', 'N/A']: return np.nan
    try: return float(s)
    except: return np.nan

def parse_stock_file(ticker):
    t_clean = 'TATAMOTORS' if ticker in ['TMPV', 'TMCV'] else ticker.upper().strip()
    fpath = os.path.join(CACHE_DIR, f"{t_clean}.html")
    if not os.path.exists(fpath): return None

    with open(fpath, "r", encoding="utf-8") as f:
        html = f.read()
    if len(html) < 5000: return None

    cid_m = re.search(r'data-row-company-id=\"(\d+)\"', html) or re.search(r'/api/company/(\d+)/', html)
    cid = cid_m.group(1) if cid_m else None

    # Ratios Topbox
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

    sales_g = compound.get('Compounded Sales Growth_3 Years', compound.get('Compounded Sales Growth_5 Years', 12.0))
    roce = ratios.get('ROCE', rt.get('ROCE %', np.nan))
    pe = ratios.get('Stock P/E', np.nan)
    opm = pl.get('OPM %', pl.get('Financing Margin %', np.nan))
    de = (borrowings / nw) if nw > 0 else 0.0
    cfo_pat = (cfo / pat) if (cfo is not None and pat and pat > 0) else 1.0
    wc = rt.get('Working Capital Days', np.nan)

    return {
        'symbol': ticker,
        'cid': cid,
        'roce': roce,
        'hist_sales_cagr': sales_g,
        'opm_expansion_3y': opm,
        'debt_to_equity': de,
        'cfo_to_pat': cfo_pat,
        'wc_days': wc,
        'pe_ratio': pe
    }

def has_sufficient_history(symbol, min_price_years=2.8, min_pl_years=3):
    """
    Excludes any company that does not possess sufficient historical track record:
      - At least 2.8 years of continuous daily price history (covering the 3Y investment window).
      - At least 3 annual reporting periods in audited profit & loss statements.
    """
    t_clean = 'TATAMOTORS' if symbol in ['TMPV', 'TMCV'] else symbol.upper().strip()
    pf = os.path.join(CACHE_DIR, f"{t_clean}_price.csv")
    hf = os.path.join(CACHE_DIR, f"{t_clean}.html")
    if not os.path.exists(pf):
        return False, "no_price_file"
    try:
        df = pd.read_csv(pf)
        dcol = [c for c in df.columns if c.lower() == 'date'][0]
        df[dcol] = pd.to_datetime(df[dcol])
        years = (df[dcol].max() - df[dcol].min()).days / 365.25
        if years < min_price_years:
            return False, f"price_years_{years:.2f}_lt_{min_price_years}"
    except:
        return False, "price_parse_error"
        
    if not os.path.exists(hf):
        return False, "no_html_file"
    try:
        with open(hf, "r", encoding="utf-8") as f:
            html = f.read()
        pos = html.find('id="profit-loss"')
        if pos == -1:
            return False, "no_pl_section"
        sec = html[pos:html.find('</section>', pos)]
        thead = re.search(r'<thead>(.*?)</thead>', sec, re.DOTALL)
        if not thead:
            return False, "no_pl_thead"
        ths = re.findall(r'<th[^>]*>(.*?)</th>', thead.group(1), re.DOTALL)
        pl_years = len(ths) - 1
        if pl_years < min_pl_years:
            return False, f"pl_years_{pl_years}_lt_{min_pl_years}"
    except:
        return False, "html_parse_error"
        
    return True, "ok"

def get_stock_price_series(symbol):
    t_clean = 'TATAMOTORS' if symbol in ['TMPV', 'TMCV'] else symbol.upper().strip()
    cache = os.path.join(CACHE_DIR, f"{t_clean}_price.csv")
    if os.path.exists(cache) and os.path.getsize(cache) > 100:
        df = pd.read_csv(cache, parse_dates=['date']).dropna().drop_duplicates('date').sort_values('date')
        if len(df) > 15:
            return df.set_index('date')['price']
    return None

def compute_stock_3y_cagr(series):
    if series is None or len(series) < 50:
        return np.nan
    first_p = float(series.iloc[0])
    last_p = float(series.iloc[-1])
    days = (series.index[-1] - series.index[0]).days
    if days < 365 * 2.5 or first_p <= 0:
        return np.nan
    years = days / 365.25
    return ((last_p / first_p) ** (1.0 / years) - 1.0)

def evaluate_combination(universe_name, model_name, universe_df, model_weights):
    """Evaluates a single model on a single universe, filtering out stocks with insufficient history."""
    u_stocks = universe_df[universe_df['Benchmark_Index'] == universe_name].copy()
    meta_dict = u_stocks.set_index('Symbol').to_dict(orient='index')
    
    # Filter for sufficient history (price history >= 2.8y and P&L >= 3y)
    valid_symbols = [s for s in u_stocks['Symbol'] if has_sufficient_history(s)[0]]
    
    parsed = []
    for s in valid_symbols:
        d = parse_stock_file(s)
        if d:
            d['name'] = meta_dict[s]['Company Name']
            d['industry'] = meta_dict[s]['Industry']
            parsed.append(d)
            
    df = pd.DataFrame(parsed)
    
    # Winsorize / standardize within universe
    for c in ['roce', 'hist_sales_cagr', 'opm_expansion_3y', 'debt_to_equity', 'cfo_to_pat', 'wc_days']:
        df[c] = df[c].fillna(df[c].median()).clip(df[c].quantile(0.02), df[c].quantile(0.98))
        mean_c, std_c = df[c].mean(), df[c].std()
        df[f'{c}_z'] = (df[c] - mean_c) / std_c if std_c > 0 else 0.0
        
    df['pe_ratio'] = df['pe_ratio'].fillna(df['pe_ratio'].median()).clip(5.0, 150.0)
    
    # Calculate model score
    score = 0.0
    for f, w in model_weights.items():
        sign = -1.0 if f in ['debt_to_equity', 'wc_days'] else 1.0
        score += w * (sign * df[f'{f}_z'])
        
    # Valuation penalty for extreme multiples (> 75 P/E)
    df['pe_penalty'] = np.where(df['pe_ratio'] > 75, (df['pe_ratio'] - 75) / 100, 0.0)
    df['final_score'] = score - 0.15 * df['pe_penalty']
    
    # Sector diversification: select top 20 with max 4 stocks per industry
    df_sorted = df.sort_values('final_score', ascending=False)
    selected = []
    ind_counts = {}
    for _, row in df_sorted.iterrows():
        ind = row['industry']
        if ind_counts.get(ind, 0) < 4:
            selected.append(row)
            ind_counts[ind] = ind_counts.get(ind, 0) + 1
        if len(selected) == 20:
            break
            
    top20_df = pd.DataFrame(selected).reset_index(drop=True)
    
    # Load actual price histories
    price_dict = {}
    stock_cagrs = {}
    for _, r in top20_df.iterrows():
        sym = r['symbol']
        p_series = get_stock_price_series(sym)
        if p_series is not None and len(p_series) > 15:
            price_dict[sym] = p_series
            stock_cagrs[sym] = compute_stock_3y_cagr(p_series)
            
    # Equal-Weighted CAGR
    valid_cagrs = [c for c in stock_cagrs.values() if pd.notnull(c)]
    ew_cagr = np.mean(valid_cagrs) if valid_cagrs else 0.0
    
    # Sample Covariance Matrix & Max-Sharpe Optimization
    prices_df = pd.DataFrame(price_dict).pct_change().dropna(how='all')
    cov = prices_df.cov() * 252.0
    cov = cov.fillna(cov.median().median() if not cov.empty else 0.04)
    
    valid_syms = list(price_dict.keys())
    N = len(valid_syms)
    mu_arr = np.array([ew_cagr if (s not in stock_cagrs or pd.isna(stock_cagrs[s])) else stock_cagrs[s] for s in valid_syms])
    cov_arr = cov.loc[valid_syms, valid_syms].values
    
    rf = 0.07 # 7% Risk-Free Rate
    def neg_sharpe(w):
        p_ret = np.dot(w, mu_arr)
        p_vol = np.sqrt(np.dot(w.T, np.dot(cov_arr, w)))
        return -(p_ret - rf) / p_vol if p_vol > 0 else 0.0
        
    init_w = np.ones(N) / N
    bounds = tuple((0.025, 0.10) for _ in range(N))
    cons = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
    res_opt = minimize(neg_sharpe, init_w, method='SLSQP', bounds=bounds, constraints=cons)
    
    opt_w = res_opt.x if res_opt.success else init_w
    port_cagr = float(np.dot(opt_w, mu_arr))
    port_vol = float(np.sqrt(np.dot(opt_w.T, np.dot(cov_arr, opt_w))))
    port_sharpe = float((port_cagr - rf) / port_vol) if port_vol > 0 else 0.0
    
    bm_stats = BENCHMARKS[universe_name]
    active_alpha = port_cagr - bm_stats['cagr']
    sharpe_delta = port_sharpe - bm_stats['sharpe']
    beats_benchmark = active_alpha > 0.0
    
    return {
        'universe': universe_name,
        'model': model_name,
        'selected_stocks': valid_syms,
        'stock_cagrs': stock_cagrs,
        'ew_cagr': float(ew_cagr),
        'opt_cagr': float(port_cagr),
        'opt_vol': float(port_vol),
        'opt_sharpe': float(port_sharpe),
        'bm_cagr': float(bm_stats['cagr']),
        'bm_vol': float(bm_stats['volatility']),
        'bm_sharpe': float(bm_stats['sharpe']),
        'active_alpha': float(active_alpha),
        'sharpe_delta': float(sharpe_delta),
        'beats_benchmark': bool(beats_benchmark)
    }

def main():
    universe_df = pd.read_csv(UNIVERSE_CSV)
    with open(CALIBRATION_JSON, "r") as f:
        calib = json.load(f)
        
    models = {
        'NIFTY 50 Model': calib['NIFTY 50']['unrounded_weights'],
        'NIFTY NEXT 50 Model': calib['NIFTY NEXT 50']['unrounded_weights'],
        'NIFTY MIDCAP 150 Model': calib['NIFTY MIDCAP 150']['unrounded_weights']
    }
    
    universe_names = ['NIFTY 50', 'NIFTY NEXT 50', 'NIFTY MIDCAP 150']
    
    matrix_results = {}
    print("\n" + "="*95)
    print("RUNNING 3x3 CROSS-UNIVERSE FACTOR TRANSFERABILITY EXPERIMENT")
    print("="*95)
    
    for u in universe_names:
        matrix_results[u] = {}
        for m in models:
            res = evaluate_combination(u, m, universe_df, models[m])
            matrix_results[u][m] = res
            status = "[BEATS BENCHMARK]" if res['beats_benchmark'] else "[LAGGED]"
            print(f"Universe: {u:<16} | Model: {m:<22} | Opt CAGR: {res['opt_cagr']*100:6.2f}% | EW CAGR: {res['ew_cagr']*100:6.2f}% | Sharpe: {res['opt_sharpe']:4.2f} | Alpha: {res['active_alpha']*100:+6.2f}% {status}")
            
    with open(os.path.join(SCRATCH_DIR, "cross_universe_matrix_results.json"), "w") as f:
        json.dump(matrix_results, f, indent=2)
        
    print("\nResults successfully saved to cross_universe_matrix_results.json.")

if __name__ == '__main__':
    main()
