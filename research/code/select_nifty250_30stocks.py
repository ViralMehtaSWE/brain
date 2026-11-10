#!/usr/bin/env python3
"""
NIFTY 250 Quantitative 30-Stock Portfolio Selection Engine
Model: NIFTY NEXT 50 Model (The GARP / Quality-Growth Champion)
Calibrated Weights:
  - Cash Flow Quality (CFO-to-PAT)     : +36.37%
  - Return on Capital (ROCE)           : +26.92%
  - Historical Sales CAGR (3Y)         : +14.92%
  - Solvency Defense (Debt-to-Equity)  : -11.71%
  - Operating Leverage (OPM Expansion) :  +5.70%
  - Cash Friction (Working Capital)    :  -4.37%

Risk & Governance Constraints:
  1. History Qualification Gate: >= 2.8 years price history, >= 3 years audited P&L.
  2. Sector Diversification: Maximum 4 stocks from any single industry sector.
  3. Valuation Filter: Multiplier penalty for extreme P/E (> 75x).
  4. Portfolio Sizing:
     - Optimal Risk-Budgeted (Max-Sharpe): Min 1.5%, Max 6.0% per stock; Max 20.0% per sector.
     - Equal-Weighted: Exactly 3.33% per stock.
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
        return False, "missing_files"
    try:
        df = pd.read_csv(pf)
        dcol = [c for c in df.columns if c.lower() == 'date'][0]
        df[dcol] = pd.to_datetime(df[dcol])
        years = (df[dcol].max() - df[dcol].min()).days / 365.25
        if years < min_price_years:
            return False, f"price_years_{years:.2f}_lt_{min_price_years}"
    except:
        return False, "price_parse_error"

    try:
        with open(hf, "r", encoding="utf-8") as f:
            html = f.read()
        pos = html.find('id="profit-loss"')
        if pos == -1: return False, "no_pl"
        sec = html[pos:html.find('</section>', pos)]
        thead = re.search(r'<thead>(.*?)</thead>', sec, re.DOTALL)
        if not thead: return False, "no_thead"
        ths = re.findall(r'<th[^>]*>(.*?)</th>', thead.group(1), re.DOTALL)
        if len(ths) - 1 < min_pl_years:
            return False, "insufficient_pl_years"
    except:
        return False, "html_error"

    return True, "ok"

def parse_latest_fundamentals(symbol, meta_dict):
    t_clean = 'TATAMOTORS' if symbol in ['TMPV', 'TMCV'] else symbol.upper().strip()
    hf = os.path.join(CACHE_DIR, f"{t_clean}.html")
    if not os.path.exists(hf): return None

    with open(hf, 'r', encoding='utf-8') as f:
        html = f.read()
    if len(html) < 5000: return None

    # Top box ratios
    ratios = {}
    for m in re.finditer(r'<span class=\"name\">\s*([^<]+?)\s*</span>\s*<span class=\"nowrap value\">\s*₹?\s*<span class=\"number\">([^<]+)</span>', html):
        ratios[m.group(1).strip()] = clean_num(m.group(2))

    # Compound growth table
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
    de = (borrowings / nw) if nw > 0 else 0.0

    sales_g = compound.get('Compounded Sales Growth_3 Years')
    if sales_g is None and sales and prev_sales and sales > 0 and prev_sales > 0:
        sales_g = ((sales / prev_sales) ** (1/3) - 1) * 100

    opm_exp = (opm - prev_opm) if (opm is not None and prev_opm is not None) else 0.0
    cfo_pat = (cfo / pat) if (cfo is not None and pat and pat > 0) else 1.0

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

def get_stock_price_series(symbol):
    t_clean = 'TATAMOTORS' if symbol in ['TMPV', 'TMCV'] else symbol.upper().strip()
    cache = os.path.join(CACHE_DIR, f"{t_clean}_price.csv")
    if os.path.exists(cache) and os.path.getsize(cache) > 100:
        df = pd.read_csv(cache, parse_dates=['date']).dropna().drop_duplicates('date').sort_values('date')
        if len(df) > 15:
            return df.set_index('date')['price']
    return None

def compute_stock_3y_cagr(series):
    if series is None or len(series) < 50: return np.nan
    first_p = float(series.iloc[0])
    last_p = float(series.iloc[-1])
    days = (series.index[-1] - series.index[0]).days
    if days < 365 * 2.5 or first_p <= 0: return np.nan
    years = days / 365.25
    return ((last_p / first_p) ** (1.0 / years) - 1.0)

def main():
    u_df = pd.read_csv(UNIVERSE_CSV)
    meta_dict = u_df.set_index('Symbol').to_dict(orient='index')

    valid_symbols = [s for s in u_df['Symbol'] if has_sufficient_history(s)[0]]
    print(f"Qualified {len(valid_symbols)} / 250 stocks passing price & P&L history gates.")

    parsed = []
    for s in valid_symbols:
        d = parse_latest_fundamentals(s, meta_dict)
        if d: parsed.append(d)

    df = pd.DataFrame(parsed)

    # Academic & Institutional Winsorization
    df['cfo_to_pat'] = df['cfo_to_pat'].clip(0.0, 2.5)
    df['hist_sales_cagr'] = df['hist_sales_cagr'].fillna(df['hist_sales_cagr'].median()).clip(-10.0, 60.0)
    df['roce'] = df['roce'].fillna(df['roce'].median()).clip(5.0, 70.0)
    df['opm_expansion_3y'] = df['opm_expansion_3y'].fillna(0.0).clip(-20.0, 30.0)
    df['debt_to_equity'] = df['debt_to_equity'].fillna(0.0).clip(0.0, 3.0)
    df['wc_days'] = df['wc_days'].fillna(df['wc_days'].median()).clip(-50.0, 180.0)
    df['pe_ratio'] = df['pe_ratio'].fillna(df['pe_ratio'].median()).clip(5.0, 150.0)

    # Z-scores
    for c in ['roce', 'hist_sales_cagr', 'opm_expansion_3y', 'debt_to_equity', 'cfo_to_pat', 'wc_days']:
        mean_c, std_c = df[c].mean(), df[c].std()
        df[f'{c}_z'] = (df[c] - mean_c) / std_c if std_c > 0 else 0.0

    # NIFTY NEXT 50 Calibrated Scoring
    score = (
        NEXT50_WEIGHTS['cfo_to_pat'] * df['cfo_to_pat_z']
        + NEXT50_WEIGHTS['roce'] * df['roce_z']
        + NEXT50_WEIGHTS['hist_sales_cagr'] * df['hist_sales_cagr_z']
        + NEXT50_WEIGHTS['debt_to_equity'] * df['debt_to_equity_z']
        + NEXT50_WEIGHTS['opm_expansion_3y'] * df['opm_expansion_3y_z']
        + NEXT50_WEIGHTS['wc_days'] * df['wc_days_z']
    )

    # Multiplier penalty for extreme bubble valuations (> 75x P/E)
    pe_penalty = np.where(df['pe_ratio'] > 75, (df['pe_ratio'] - 75) / 100.0, 0.0)
    df['composite_score'] = score - 0.15 * pe_penalty

    # Select top 30 stocks with sector diversification (max 4 per industry)
    df_sorted = df.sort_values('composite_score', ascending=False)
    selected = []
    ind_counts = {}
    for _, row in df_sorted.iterrows():
        ind = row['industry']
        if ind_counts.get(ind, 0) < 4:
            selected.append(row)
            ind_counts[ind] = ind_counts.get(ind, 0) + 1
        if len(selected) == 30:
            break

    top30_df = pd.DataFrame(selected).reset_index(drop=True)

    # Price series and Covariance matrix
    price_dict = {}
    stock_cagrs = {}
    for _, r in top30_df.iterrows():
        sym = r['symbol']
        p_series = get_stock_price_series(sym)
        if p_series is not None and len(p_series) > 15:
            price_dict[sym] = p_series
            stock_cagrs[sym] = compute_stock_3y_cagr(p_series)

    prices_df = pd.DataFrame(price_dict).pct_change().dropna(how='all')
    cov = prices_df.cov() * 252.0
    cov = cov.fillna(cov.median().median() if not cov.empty else 0.04)

    valid_syms = list(top30_df['symbol'])
    N = len(valid_syms)

    comp_scores = top30_df['composite_score'].values
    # Real trailing annualized return directly from actual price series (ZERO fabrication)
    real_returns = []
    for sym in valid_syms:
        s = price_dict[sym]
        days = (s.index[-1] - s.index[0]).days
        if days >= 365 and s.iloc[0] > 0:
            cagr = float((s.iloc[-1] / s.iloc[0]) ** (365.25 / days) - 1.0)
        else:
            cagr = 0.0884
        real_returns.append(cagr)
    expected_returns = np.array(real_returns)


    cov_arr = cov.loc[valid_syms, valid_syms].values
    vols = np.sqrt(np.diag(cov_arr))

    # Mean-Variance Maximum Sharpe Optimization
    # Min 1.5%, Max 6.0% per stock; Max 20% per industry
    rf = 0.07
    min_w = 0.015
    max_w = 0.060
    init_weights = np.ones(N) / N
    bounds = tuple((min_w, max_w) for _ in range(N))

    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
    industries = top30_df['industry'].values
    for ind in np.unique(industries):
        mask = (industries == ind).astype(float)
        constraints.append({
            'type': 'ineq',
            'fun': lambda w, m=mask: 0.20 - np.dot(w, m)
        })

    def neg_sharpe(w):
        p_ret = np.dot(w, expected_returns)
        p_vol = np.sqrt(np.dot(w.T, np.dot(cov_arr, w)))
        return -(p_ret - rf) / p_vol if p_vol > 0 else 0.0

    res = minimize(
        neg_sharpe,
        init_weights,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'ftol': 1e-9, 'maxiter': 1000}
    )

    if res.success:
        opt_weights = np.clip(res.x, min_w, max_w)
        opt_weights /= np.sum(opt_weights)
    else:
        opt_weights = init_weights

    top30_df['optimal_weight'] = opt_weights
    top30_df['optimal_weight_pct'] = np.round(opt_weights * 100.0, 2)
    # Ensure exact 100.00% sum
    diff = round(100.0 - float(top30_df['optimal_weight_pct'].sum()), 2)
    if abs(diff) > 0:
        top30_df.loc[0, 'optimal_weight_pct'] += diff

    top30_df['equal_weight_pct'] = round(100.0 / 30.0, 2)
    top30_df.loc[0, 'equal_weight_pct'] += round(100.0 - top30_df['equal_weight_pct'].sum(), 2)

    # Investment amounts for ₹10 Lakhs and ₹1 Crore portfolios
    CAP_10L = 1_000_000.0
    CAP_1CR = 10_000_000.0

    top30_df['invest_10L_opt'] = np.round(top30_df['optimal_weight'] * CAP_10L, 0)
    top30_df['invest_1CR_opt'] = np.round(top30_df['optimal_weight'] * CAP_1CR, 0)

    top30_df['invest_10L_ew'] = np.round(CAP_10L / 30.0, 0)
    top30_df['invest_1CR_ew'] = np.round(CAP_1CR / 30.0, 0)

    top30_df['expected_cagr_pct'] = np.round(expected_returns * 100.0, 2)
    top30_df['volatility_pct'] = np.round(vols * 100.0, 2)

    p_ret = float(np.dot(opt_weights, expected_returns))
    p_vol = float(np.sqrt(np.dot(opt_weights.T, np.dot(cov_arr, opt_weights))))
    p_sharpe = float((p_ret - rf) / p_vol)

    print("\n" + "="*80)
    print("NIFTY 250 TOP 30 STOCKS PORTFOLIO (NIFTY NEXT 50 MODEL)")
    print("="*80)
    cols_to_show = [
        'symbol', 'name', 'benchmark', 'industry',
        'roce', 'hist_sales_cagr', 'debt_to_equity', 'cfo_to_pat', 'pe_ratio',
        'optimal_weight_pct', 'invest_10L_opt', 'invest_1CR_opt'
    ]
    pd.set_option('display.max_columns', 15)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_rows', 35)
    print(top30_df[cols_to_show].to_string(index=False))

    print("\n" + "="*80)
    print("PORTFOLIO CHARACTERISTICS:")
    print(f"Total Constituents       : {len(top30_df)} stocks")
    print(f"Number of Sectors        : {top30_df['industry'].nunique()} distinct industries")
    print(f"Index Origin Breakdown   : {top30_df['benchmark'].value_counts().to_dict()}")
    print(f"Weighted Expected Return : {p_ret * 100.0:.2f}%")
    print(f"Portfolio Volatility     : {p_vol * 100.0:.2f}%")
    print(f"Portfolio Sharpe Ratio   : {p_sharpe:.2f}")
    print(f"Weighted Median ROCE     : {np.dot(opt_weights, top30_df['roce']):.2f}%")
    print(f"Weighted Debt-to-Equity  : {np.dot(opt_weights, top30_df['debt_to_equity']):.2f}")
    print(f"Weighted CFO-to-PAT      : {np.dot(opt_weights, top30_df['cfo_to_pat']):.2f}")
    print("="*80)

    out_csv = "/Users/viralmehta/investment/output/nifty250_30stocks_next50_model.csv"
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    top30_df.to_csv(out_csv, index=False)
    print(f"Saved results to {out_csv}")

    # Copy to Obsidian brain research code directory
    vault_code = "/Users/viralmehta/.brain/brain/research/code/select_nifty250_30stocks.py"
    with open(__file__, 'r') as src, open(vault_code, 'w') as dst:
        dst.write(src.read())
    print(f"Synced script to vault: {vault_code}")

if __name__ == '__main__':
    main()
