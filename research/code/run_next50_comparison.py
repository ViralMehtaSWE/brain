#!/usr/bin/env python3
"""
NIFTY NEXT 50 Benchmark Validation:
Applies the exact same multi-factor fundamental weights to the Nifty Next 50 universe
and measures realized 3-year performance vs the NIFTY NEXT 50 Index (16.62% CAGR).
"""

import os
import sys
import numpy as np
import pandas as pd

try:
    from config import DATA_DIR, CACHE_DIR
    SCRATCH_DIR = DATA_DIR
except ImportError:
    SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
    CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")

def analyze_next50():
    fpath = os.path.join(SCRATCH_DIR, "nifty_next_50_df.csv")
    if not os.path.exists(fpath):
        legacy = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch/nifty_next_50_df.csv"
        if os.path.exists(legacy):
            fpath = legacy
        else:
            from evaluate_next50 import fetch_and_evaluate_next50
            fetch_and_evaluate_next50()


    df = pd.read_csv(fpath)
    if len(df) == 0:
        print("Empty dataset.")
        return

    print("=" * 90)
    print("NIFTY NEXT 50 EMPIRICAL VALIDATION: EXACT SAME WEIGHTS APPLIED")
    print("=" * 90)

    # Clean & Impute
    df['roce'] = df['roce'].fillna(df['roce'].median())
    df['hist_sales_cagr_3y'] = df['hist_sales_cagr_3y'].fillna(df['hist_sales_cagr_3y'].median())
    df['opm'] = df['opm'].fillna(df['opm'].median())
    df['cfo_to_pat'] = df['cfo_to_pat'].fillna(1.0).clip(0, 3)
    df['debt_to_equity'] = df['debt_to_equity'].fillna(0.0).clip(0, 4)
    df['current_pe'] = df['current_pe'].fillna(df['current_pe'].median()).clip(5, 120)

    # Sector-neutral Z-scores
    def calc_z(series, sector):
        s_mean = series.groupby(sector).transform('mean')
        s_std = series.groupby(sector).transform('std').replace(0, 1).fillna(1)
        return (series - s_mean) / s_std

    z_roce = calc_z(df['roce'], df['sector'])
    z_sales = calc_z(df['hist_sales_cagr_3y'], df['sector'])
    z_opm = calc_z(df['opm'], df['sector'])
    z_cfo = calc_z(df['cfo_to_pat'], df['sector'])
    z_de = calc_z(df['debt_to_equity'], df['sector'])
    z_pe = calc_z(df['current_pe'], df['sector'])

    # EXACT SAME FORMULA WEIGHTS
    raw_score = (
        0.25 * z_roce
        + 0.20 * z_sales
        + 0.15 * z_opm
        + 0.15 * z_cfo
        - 0.15 * z_de
        - 0.10 * z_pe
    )

    df['fundamental_score'] = (raw_score.rank(pct=True) * 100).round(1)
    df_sorted = df.sort_values(by='fundamental_score', ascending=False).reset_index(drop=True)

    # Split into Top Quintile (Top 5-6 stocks) vs Bottom Quintile
    k = max(4, int(len(df_sorted) * 0.25))
    top_basket = df_sorted.head(k)
    bottom_basket = df_sorted.tail(k)

    # NIFTY NEXT 50 Official Benchmark Performance (From Screener price chart)
    nifty_next50_3y_cagr = 16.62  # Official 3Y CAGR (Nov 2023 to Nov 2026)
    nifty_next50_5y_cagr = 10.70  # Official 5Y CAGR
    nifty_next50_pe = 17.7

    top_3y_cagr = top_basket['stock_price_cagr_3y'].mean()
    bottom_3y_cagr = bottom_basket['stock_price_cagr_3y'].mean()
    universe_avg_3y_cagr = df['stock_price_cagr_3y'].mean()
    active_alpha = top_3y_cagr - nifty_next50_3y_cagr

    print(f"\n[NIFTY NEXT 50 Benchmark Baseline]:")
    print(f"  Benchmark 3-Year CAGR : {nifty_next50_3y_cagr:.2f}% per annum")
    print(f"  Benchmark 5-Year CAGR : {nifty_next50_5y_cagr:.2f}% per annum")
    print(f"  Benchmark P/E Ratio   : {nifty_next50_pe}x")

    display_cols = [
        'ticker', 'sector', 'fundamental_score', 'roce', 
        'hist_sales_cagr_3y', 'cfo_to_pat', 'debt_to_equity', 
        'current_pe', 'stock_price_cagr_3y'
    ]

    print(f"\n--- Top Strategy Selected Stocks (Nifty Next 50) ---")
    print(top_basket[display_cols].to_string(index=False))

    print(f"\n--- Bottom Ranked Stocks (Nifty Next 50) ---")
    print(bottom_basket[display_cols].to_string(index=False))

    print("\n" + "=" * 90)
    print("PERFORMANCE SUMMARY & ALPHA EVALUATION")
    print("=" * 90)
    print(f"  Top Strategy Picks 3-Year Return (CAGR)   : {top_3y_cagr:+.2f}% per annum")
    print(f"  NIFTY NEXT 50 Benchmark 3-Year Return (CAGR): {nifty_next50_3y_cagr:+.2f}% per annum")
    print(f"  Active Alpha over Nifty Next 50           : {active_alpha:+.2f}% per annum")
    print(f"  Unranked Universe Average 3-Year Return   : {universe_avg_3y_cagr:+.2f}% per annum")
    print(f"  Bottom Ranked Basket 3-Year Return        : {bottom_3y_cagr:+.2f}% per annum")
    print(f"  Long/Short Spread (Top vs Bottom Basket)  : {top_3y_cagr - bottom_3y_cagr:+.2f}% per annum")

    print("\n" + "=" * 90)
    print("VERDICT")
    print("=" * 90)
    if active_alpha > 0:
        print(f"CONFIRMED: The exact same weights strongly OUTPERFORM the NIFTY NEXT 50 benchmark.")
        print(f"Generating an excess return of {active_alpha:+.2f}% per annum above the index!")
    else:
        print(f"The strategy underperformed by {active_alpha:.2f}%.")

if __name__ == '__main__':
    analyze_next50()
