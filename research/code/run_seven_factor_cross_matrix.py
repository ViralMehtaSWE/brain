#!/usr/bin/env python3
"""
Regenerate 3x3 Cross-Universe Factor Matrix with P/E as an Explicit Feature
Models Evaluated (7-Factor Empirically Calibrated):
  1. NIFTY 50 Model (P/E: -17.52%)
  2. NIFTY NEXT 50 Model (P/E: -16.52%)
  3. NIFTY MIDCAP 150 Model (P/E: -33.40%)

Universes Tested:
  - NIFTY 50 (Benchmark: +8.84%)
  - NIFTY NEXT 50 (Benchmark: +16.62%)
  - NIFTY MIDCAP 150 (Benchmark: +18.50%)
"""

import os
import sys, re
import numpy as np
import pandas as pd
from scipy.optimize import minimize

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")
UNIVERSE_CSV = os.path.join(SCRATCH_DIR, "nifty_250_universe.csv")

sys.path.insert(0, '/Users/viralmehta/investment')
from generate_10_and_30_portfolios import (
    parse_latest_fundamentals,
    get_stock_series,
    has_sufficient_history
)

BENCHMARKS = {
    'NIFTY 50': 0.0884,
    'NIFTY NEXT 50': 0.1662,
    'NIFTY MIDCAP 150': 0.1850
}

# Empirically Calibrated 7-Factor Weights (with PE ratio)
SEVEN_FACTOR_MODELS = {
    'NIFTY 50 Model (7F)': {
        'opm_expansion_3y': 0.2441,
        'hist_sales_cagr': 0.2383,
        'pe_ratio': -0.1752,
        'wc_days': -0.1313,
        'roce': 0.0905,
        'debt_to_equity': -0.0789,
        'cfo_to_pat': 0.0417
    },
    'NIFTY NEXT 50 Model (7F)': {
        'hist_sales_cagr': 0.2457,
        'pe_ratio': -0.1652,
        'opm_expansion_3y': 0.1486,
        'debt_to_equity': -0.1358,
        'roce': 0.1203,
        'cfo_to_pat': 0.1094,
        'wc_days': -0.0751
    },
    'NIFTY MIDCAP 150 Model (7F)': {
        'pe_ratio': -0.3340,
        'hist_sales_cagr': 0.1434,
        'cfo_to_pat': 0.1431,
        'opm_expansion_3y': 0.1260,
        'debt_to_equity': -0.0961,
        'wc_days': -0.0901,
        'roce': 0.0671
    }
}

def compute_stock_3y_cagr(series):
    if series is None or len(series) < 50: return np.nan
    first_p = float(series.iloc[0])
    last_p = float(series.iloc[-1])
    days = (series.index[-1] - series.index[0]).days
    if days < 365 * 2.5 or first_p <= 0: return np.nan
    years = days / 365.25
    return ((last_p / first_p) ** (1.0 / years) - 1.0)

def evaluate_static_3y(universe_df, universe_name, model_weights, top_k=20):
    u_stocks = universe_df[universe_df['Benchmark_Index'] == universe_name].copy()
    meta_dict = u_stocks.set_index('Symbol').to_dict(orient='index')
    valid_symbols = [s for s in u_stocks['Symbol'] if has_sufficient_history(s)]

    parsed = []
    for s in valid_symbols:
        d = parse_latest_fundamentals(s, meta_dict)
        if d: parsed.append(d)

    df = pd.DataFrame(parsed)

    df['cfo_to_pat'] = df['cfo_to_pat'].clip(0.0, 2.5)
    for c in ['roce', 'hist_sales_cagr', 'opm_expansion_3y', 'debt_to_equity', 'cfo_to_pat', 'wc_days', 'pe_ratio']:
        df[c] = df[c].fillna(df[c].median()).clip(df[c].quantile(0.02), df[c].quantile(0.98))
        mean_c, std_c = df[c].mean(), df[c].std()
        df[f'{c}_z'] = (df[c] - mean_c) / std_c if std_c > 0 else 0.0

    # Score directly from 7-factor model (NO arbitrary penalty!)
    score = 0.0
    for f, w in model_weights.items():
        score += w * df[f'{f}_z']
    df['final_score'] = score

    # Diversification: max 4 per sector
    df_sorted = df.sort_values('final_score', ascending=False)
    selected = []
    ind_counts = {}
    for _, row in df_sorted.iterrows():
        ind = row['industry']
        if ind_counts.get(ind, 0) < 4:
            selected.append(row['symbol'])
            ind_counts[ind] = ind_counts.get(ind, 0) + 1
        if len(selected) == top_k: break

    # Performance
    price_dict = {}
    stock_cagrs = {}
    for sym in selected:
        p_s = get_stock_series(sym)
        if p_s is not None and len(p_s) > 15:
            price_dict[sym] = p_s
            stock_cagrs[sym] = compute_stock_3y_cagr(p_s)

    valid_cagrs = [c for c in stock_cagrs.values() if pd.notnull(c)]
    ew_cagr = np.mean(valid_cagrs) if valid_cagrs else 0.0

    prices_df = pd.DataFrame(price_dict).pct_change().dropna(how='all')
    cov = prices_df.cov() * 252.0
    cov = cov.fillna(cov.median().median() if not cov.empty else 0.04)

    valid_syms = list(price_dict.keys())
    N = len(valid_syms)
    mu_arr = np.array([ew_cagr if (s not in stock_cagrs or pd.isna(stock_cagrs[s])) else stock_cagrs[s] for s in valid_syms])
    cov_arr = cov.loc[valid_syms, valid_syms].values

    rf = 0.07
    min_w, max_w = 0.025, min(0.12, 2.0 / N)
    bounds = tuple((min_w, max_w) for _ in range(N))
    init_w = np.ones(N) / N
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

    def neg_sharpe(w):
        p_ret = np.dot(w, mu_arr)
        p_vol = np.sqrt(np.dot(w.T, np.dot(cov_arr, w)))
        return -(p_ret - rf) / p_vol if p_vol > 0 else 0.0

    res = minimize(neg_sharpe, init_w, method='SLSQP', bounds=bounds, constraints=constraints)
    if res.success:
        opt_w = np.clip(res.x, min_w, max_w)
        opt_w /= np.sum(opt_w)
    else:
        opt_w = init_w

    opt_cagr = float(np.dot(opt_w, mu_arr))
    opt_vol = float(np.sqrt(np.dot(opt_w.T, np.dot(cov_arr, opt_w))))
    opt_sharpe = float((opt_cagr - rf) / opt_vol) if opt_vol > 0 else 0.0

    # Sector metrics
    sub_df = df[df['symbol'].isin(selected)]
    avg_pe = float(sub_df['pe_ratio'].mean())
    avg_roce = float(sub_df['roce'].mean())

    return {
        'selected_stocks': selected,
        'ew_cagr': ew_cagr,
        'opt_cagr': opt_cagr,
        'opt_vol': opt_vol,
        'opt_sharpe': opt_sharpe,
        'avg_pe': avg_pe,
        'avg_roce': avg_roce
    }

def run_annual_rebalance(universe_df, universe_name, model_weights, top_k=20):
    rebalance_dates = [
        pd.Timestamp('2023-11-13'),
        pd.Timestamp('2024-11-11'),
        pd.Timestamp('2025-11-10'),
        pd.Timestamp('2026-11-10')
    ]
    filing_years = [2023, 2024, 2025]
    friction = 0.0015

    u_stocks = universe_df[universe_df['Benchmark_Index'] == universe_name].copy()
    meta_dict = u_stocks.set_index('Symbol').to_dict(orient='index')
    valid_symbols = [s for s in u_stocks['Symbol'] if has_sufficient_history(s)]

    period_returns = []

    for idx, f_yr in enumerate(filing_years):
        d_start = rebalance_dates[idx]
        d_end = rebalance_dates[idx + 1]

        parsed = []
        for sym in valid_symbols:
            t_clean = 'TATAMOTORS' if sym in ['TMPV', 'TMCV'] else sym.upper().strip()
            hf = os.path.join(CACHE_DIR, f'{t_clean}.html')
            if not os.path.exists(hf): continue
            with open(hf) as f: html = f.read()
            
            # Detailed tables
            def parse_sec(sec_id):
                pos = html.find(f'id=\"{sec_id}\"')
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

            p_curr = f'Mar {f_yr}'
            p_prev3 = f'Mar {f_yr - 3}'
            curr_pl = pl.get(p_curr, {})
            prev_pl = pl.get(p_prev3, {})
            curr_bs = bs.get(p_curr, {})
            curr_cf = cf.get(p_curr, {})
            curr_rt = rt.get(p_curr, {})

            if not curr_pl: continue

            pat = curr_pl.get('Net Profit')
            sales = curr_pl.get('Sales') or curr_pl.get('Revenue')
            prev_sales = prev_pl.get('Sales') or prev_pl.get('Revenue')
            opm = curr_pl.get('OPM %') or curr_pl.get('Financing Margin %')
            prev_opm = prev_pl.get('OPM %') or prev_pl.get('Financing Margin %')
            eps = curr_pl.get('EPS in Rs')

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

            s_series = get_stock_series(sym)
            if s_series is None: continue
            p0 = s_series.asof(d_start)
            if pd.isna(p0) or p0 <= 0: continue
            pe_c = (float(p0) / eps) if (eps and eps > 0) else np.nan

            parsed.append({
                'symbol': sym,
                'industry': meta_dict[sym]['Industry'],
                'cfo_to_pat': cfo_pat,
                'roce': roce,
                'hist_sales_cagr': sales_cagr,
                'opm_expansion_3y': opm_exp,
                'debt_to_equity': de,
                'wc_days': wc_days,
                'pe_ratio': pe_c
            })

        df = pd.DataFrame(parsed)
        df['cfo_to_pat'] = df['cfo_to_pat'].clip(0.0, 2.5)
        for c in ['roce', 'hist_sales_cagr', 'opm_expansion_3y', 'debt_to_equity', 'cfo_to_pat', 'wc_days', 'pe_ratio']:
            df[c] = df[c].fillna(df[c].median()).clip(df[c].quantile(0.02), df[c].quantile(0.98))
            mean_c, std_c = df[c].mean(), df[c].std()
            df[f'{c}_z'] = (df[c] - mean_c) / std_c if std_c > 0 else 0.0

        score = 0.0
        for f, w in model_weights.items():
            score += w * df[f'{f}_z']
        df['final_score'] = score

        df_sorted = df.sort_values('final_score', ascending=False)
        selected = []
        ind_counts = {}
        for _, row in df_sorted.iterrows():
            ind = row['industry']
            if ind_counts.get(ind, 0) < 4:
                selected.append(row['symbol'])
                ind_counts[ind] = ind_counts.get(ind, 0) + 1
            if len(selected) == top_k: break

        stock_rets = {}
        price_dict = {}
        for s in selected:
            s_s = get_stock_series(s)
            if s_s is not None:
                p0 = s_s.asof(d_start)
                p1 = s_s.asof(d_end)
                if pd.notnull(p0) and pd.notnull(p1) and p0 > 0:
                    stock_rets[s] = (float(p1) / float(p0)) - 1.0
                    sub_s = s_s.loc[(s_s.index >= d_start) & (s_s.index <= d_end)]
                    if len(sub_s) > 10: price_dict[s] = sub_s

        val_syms = [s for s in selected if s in stock_rets]
        if not val_syms:
            period_returns.append(0.0)
            continue

        r_vec = np.array([stock_rets[s] for s in val_syms])
        p_df = pd.DataFrame({s: price_dict[s] for s in val_syms if s in price_dict}).pct_change().dropna(how='all')
        cov = p_df.cov() * 52.0
        cov = cov.fillna(0.04)

        K = len(val_syms)
        cov_mat = cov.reindex(index=val_syms, columns=val_syms).fillna(0.04).values
        rf = 0.07 / 52.0
        min_w, max_w = 0.025, min(0.12, 2.0 / K)
        bounds = tuple((min_w, max_w) for _ in range(K))
        init_w = np.ones(K) / K
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

        def neg_sh(w):
            w_ret = np.dot(w, r_vec)
            w_vol = np.sqrt(np.dot(w.T, np.dot(cov_mat, w)))
            return -(w_ret - rf) / w_vol if w_vol > 0 else 0.0

        res = minimize(neg_sh, init_w, method='SLSQP', bounds=bounds, constraints=constraints)
        if res.success:
            w_opt = np.clip(res.x, min_w, max_w)
            w_opt /= np.sum(w_opt)
        else:
            w_opt = init_w

        gross_ret = float(np.dot(w_opt, r_vec))
        net_ret = gross_ret - friction
        period_returns.append(net_ret)

    cum_wealth = 1.0
    for r in period_returns:
        cum_wealth *= (1.0 + r)
    ann_cagr = (cum_wealth ** (1.0 / len(filing_years))) - 1.0

    return {
        'period_returns': period_returns,
        'cumulative_wealth': cum_wealth,
        'annual_rebalanced_cagr': ann_cagr
    }

def main():
    u_df = pd.read_csv(UNIVERSE_CSV)
    universes = ['NIFTY 50', 'NIFTY NEXT 50', 'NIFTY MIDCAP 150']

    results = []

    print("Regenerating 3x3 Cross-Universe Matrix with Calibrated P/E Feature...")
    for u_name in universes:
        bm_cagr = BENCHMARKS[u_name]
        for m_name, m_weights in SEVEN_FACTOR_MODELS.items():
            print(f"Testing {m_name} on {u_name}...")
            stat = evaluate_static_3y(u_df, u_name, m_weights, top_k=20)
            rebal = run_annual_rebalance(u_df, u_name, m_weights, top_k=20)

            results.append({
                'Universe': u_name,
                'Model': m_name,
                'Benchmark_CAGR': bm_cagr,
                'Average_PE': stat['avg_pe'],
                'Average_ROCE': stat['avg_roce'],
                'Static_EW_CAGR': stat['ew_cagr'],
                'Static_Opt_CAGR': stat['opt_cagr'],
                'Static_Alpha': stat['opt_cagr'] - bm_cagr,
                'Static_Vol': stat['opt_vol'],
                'Static_Sharpe': stat['opt_sharpe'],
                'Rebalanced_CAGR': rebal['annual_rebalanced_cagr'],
                'Rebalanced_Alpha': rebal['annual_rebalanced_cagr'] - bm_cagr,
                'Y1_Return': rebal['period_returns'][0],
                'Y2_Return': rebal['period_returns'][1],
                'Y3_Return': rebal['period_returns'][2]
            })

    res_df = pd.DataFrame(results)

    print("\n" + "="*95)
    print("REGENERATED 3x3 MATRIX (7-FACTOR MODELS WITH CALIBRATED P/E)")
    print("="*95)
    cols = ['Universe', 'Model', 'Average_PE', 'Static_Opt_CAGR', 'Static_Alpha', 'Rebalanced_CAGR', 'Rebalanced_Alpha', 'Y3_Return']
    pd.set_option('display.max_columns', 15)
    pd.set_option('display.width', 1000)
    print(res_df[cols].to_string(index=False))

    out_csv = "/Users/viralmehta/investment/output/regenerated_3x3_matrix_with_pe.csv"
    res_df.to_csv(out_csv, index=False)
    print(f"\nSaved results to {out_csv}")

if __name__ == '__main__':
    main()
