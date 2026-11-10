#!/usr/bin/env python3
"""
NIFTY 250 Empirical 7-Factor Portfolio Pipeline
Features and Empirically Calibrated Weights (from 625 point-in-time observations):
  1. pe_ratio             (-) : -25.86%  (Valuation Penalty)
  2. hist_sales_cagr      (+) : +18.62%  (Topline Growth Acceleration)
  3. opm_expansion_3y     (+) : +15.06%  (Operating Leverage Expansion)
  4. debt_to_equity       (-) : -12.63%  (Solvency Discipline)
  5. wc_days              (-) : -12.15%  (Working Capital Friction Penalty)
  6. cfo_to_pat           (+) : +10.83%  (Operating Cash Flow Quality)
  7. roce                 (+) :  +4.86%  (Capital Efficiency Floor)
"""

import os
import sys
import numpy as np
import pandas as pd
from scipy.optimize import minimize

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")
UNIVERSE_CSV = os.path.join(SCRATCH_DIR, "nifty_250_universe.csv")

sys.path.insert(0, '/Users/viralmehta/investment')
from generate_10_and_30_portfolios import (
    parse_latest_fundamentals,
    has_sufficient_history,
    build_portfolio
)

W7 = {
    'pe_ratio': -0.25855,
    'hist_sales_cagr': 0.18623,
    'opm_expansion_3y': 0.15057,
    'debt_to_equity': -0.12632,
    'wc_days': -0.12148,
    'cfo_to_pat': 0.10826,
    'roce': 0.04859
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

    for c in ['roce', 'hist_sales_cagr', 'opm_expansion_3y', 'debt_to_equity', 'cfo_to_pat', 'wc_days', 'pe_ratio']:
        mean_c, std_c = df[c].mean(), df[c].std()
        df[f'{c}_z'] = (df[c] - mean_c) / std_c if std_c > 0 else 0.0

    score = 0.0
    for f, w in W7.items():
        score += w * df[f'{f}_z']

    df['composite_score'] = score
    df_sorted = df.sort_values('composite_score', ascending=False).reset_index(drop=True)

    df_10, stats_10 = build_portfolio(K=10, max_per_sector=2, min_w=0.05, max_w=0.15, max_sec_w=0.25, scored_df=df_sorted)
    df_30, stats_30 = build_portfolio(K=30, max_per_sector=4, min_w=0.015, max_w=0.060, max_sec_w=0.20, scored_df=df_sorted)

    os.makedirs("/Users/viralmehta/investment/output", exist_ok=True)
    df_10.to_csv("/Users/viralmehta/investment/output/nifty250_7factor_top10.csv", index=False)
    df_30.to_csv("/Users/viralmehta/investment/output/nifty250_7factor_top30.csv", index=False)
    print("Successfully generated and saved 7-Factor portfolios.")

if __name__ == '__main__':
    main()
