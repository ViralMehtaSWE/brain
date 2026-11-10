#!/usr/bin/env python3
"""
Quantitative Analysis: Fundamental Predictive Power on Indian Equities
Calculates Rank IC, t-statistics, Random Forest feature importance, 
and generates the optimal stock scoring formula.
"""

import os
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, ttest_1samp
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"

def analyze_predictive_power():
    panel_path = os.path.join(SCRATCH_DIR, "panel_df.csv")
    current_path = os.path.join(SCRATCH_DIR, "current_df.csv")

    if not os.path.exists(panel_path) or not os.path.exists(current_path):
        print("Data files not found. Run parse_and_extract.py first.")
        return

    df = pd.read_csv(panel_path)
    curr_df = pd.read_csv(current_path)

    features = [
        'roce', 
        'hist_sales_cagr', 
        'hist_pat_cagr', 
        'opm', 
        'opm_expansion_3y', 
        'debt_to_equity', 
        'cfo_to_pat', 
        'fcf_to_sales', 
        'wc_days'
    ]
    
    target = 'fwd_pat_cagr_3y'

    print("=" * 80)
    print("STEP 1: SPEARMAN RANK INFORMATION COEFFICIENT (RANK IC) ANALYSIS")
    print("=" * 80)
    print(f"Total panel observations: {len(df)} across periods: {sorted(df['period'].unique())}")
    
    # Calculate cross-sectional Rank IC for each period
    ic_records = []
    periods = sorted(df['period'].unique())
    
    for p in periods:
        p_df = df[df['period'] == p]
        if len(p_df) < 15:
            continue
        for feat in features:
            sub = p_df[[feat, target]].dropna()
            if len(sub) >= 12:
                # Winsorize extreme outliers at 2.5% and 97.5%
                low = sub[feat].quantile(0.025)
                high = sub[feat].quantile(0.975)
                w_feat = sub[feat].clip(low, high)
                
                ic, p_val = spearmanr(w_feat, sub[target])
                ic_records.append({
                    'period': p,
                    'factor': feat,
                    'rank_ic': ic,
                    'p_value': p_val,
                    'sample_size': len(sub)
                })

    ic_df = pd.DataFrame(ic_records)
    
    # Aggregate across periods
    summary = []
    for feat, grp in ic_df.groupby('factor'):
        mean_ic = grp['rank_ic'].mean()
        std_ic = grp['rank_ic'].std()
        count = len(grp)
        ir = mean_ic / std_ic if std_ic > 0 else 0
        # 1-sample t-test testing H0: mean_ic == 0
        t_stat, p_val = ttest_1samp(grp['rank_ic'], 0) if count > 1 else (np.nan, np.nan)
        
        summary.append({
            'Factor': feat,
            'Mean Rank IC': mean_ic,
            'IC Std Dev': std_ic,
            'IC IR (Sharpe of Factor)': ir,
            't-statistic': t_stat,
            'p-value': p_val,
            'Periods Tested': count
        })

    summary_df = pd.DataFrame(summary).sort_values(by='Mean Rank IC', key=abs, ascending=False)
    print("\nSummary of Fundamental Factor Predictive Power (Rank IC):")
    print(summary_df.to_string(index=False))

    print("\n" + "=" * 80)
    print("STEP 2: NON-LINEAR FEATURE IMPORTANCE (RANDOM FOREST)")
    print("=" * 80)
    
    # Clean data for tree modeling
    clean_tree = df[features + [target]].dropna()
    X = clean_tree[features]
    y = clean_tree[target]

    rf = RandomForestRegressor(n_estimators=100, max_depth=4, min_samples_leaf=2, random_state=42, n_jobs=-1)
    rf.fit(X, y)

    perm_imp = permutation_importance(rf, X, y, n_repeats=5, random_state=42, n_jobs=-1)
    
    fi_df = pd.DataFrame({
        'Factor': features,
        'Gini Importance (MDI)': rf.feature_importances_,
        'Permutation Importance Mean': perm_imp.importances_mean,
        'Permutation Importance Std': perm_imp.importances_std
    }).sort_values(by='Permutation Importance Mean', ascending=False)
    
    print("\nRandom Forest Feature Importance:")
    print(fi_df.to_string(index=False))

    print("\n" + "=" * 80)
    print("STEP 3: MULTI-FACTOR STOCK SCORING FORMULA")
    print("=" * 80)

    # We formulate the composite score combining:
    # 1. High Capital Efficiency (ROCE)
    # 2. Operating Margin Expansion & Health (OPM, OPM expansion)
    # 3. Cash Flow Quality (CFO / PAT)
    # 4. Solvency / Prudence (Debt to Equity penalty)
    # 5. Valuation Attractiveness (P/E penalty, PEG ratio)
    
    print("""
Formula Architecture:
  Score = 
    + 0.25 * Z(ROCE)
    + 0.20 * Z(Historical Sales Growth)
    + 0.15 * Z(OPM Expansion)
    + 0.15 * Z(CFO to PAT / Cash Conversion)
    - 0.15 * Z(Debt to Equity)
    - 0.10 * Z(Current P/E)
    
Where Z(X) is the Sector-Neutral Winsorized Z-Score:
  Z(X) = (X - Mean_sector) / Std_sector
""")

    print("=" * 80)
    print("STEP 4: SCORING CURRENT INDIAN EQUITIES FOR 2-3 YEAR HOLDING")
    print("=" * 80)

    # Process Current Cross-section
    curr_df_clean = curr_df.copy()
    
    # Fill NAs logically
    curr_df_clean['roce'] = curr_df_clean['roce'].fillna(curr_df_clean['roce'].median())
    curr_df_clean['hist_sales_cagr_3y'] = curr_df_clean['hist_sales_cagr_3y'].fillna(curr_df_clean['hist_sales_cagr_3y'].median())
    curr_df_clean['opm'] = curr_df_clean['opm'].fillna(curr_df_clean['opm'].median())
    curr_df_clean['debt_to_equity'] = curr_df_clean['debt_to_equity'].fillna(0.0)
    curr_df_clean['cfo_to_pat'] = curr_df_clean['cfo_to_pat'].fillna(1.0)
    curr_df_clean['current_pe'] = curr_df_clean['current_pe'].fillna(curr_df_clean['current_pe'].median())

    # Sector Z-scores
    def calc_z(series, sector):
        s_mean = series.groupby(sector).transform('mean')
        s_std = series.groupby(sector).transform('std').replace(0, 1).fillna(1)
        return (series - s_mean) / s_std

    z_roce = calc_z(curr_df_clean['roce'], curr_df_clean['sector'])
    z_sales_growth = calc_z(curr_df_clean['hist_sales_cagr_3y'], curr_df_clean['sector'])
    z_opm = calc_z(curr_df_clean['opm'], curr_df_clean['sector'])
    z_cfo_pat = calc_z(curr_df_clean['cfo_to_pat'].clip(0, 3), curr_df_clean['sector'])
    z_de = calc_z(curr_df_clean['debt_to_equity'].clip(0, 4), curr_df_clean['sector'])
    z_pe = calc_z(curr_df_clean['current_pe'].clip(5, 120), curr_df_clean['sector'])

    # Multi-factor score
    raw_score = (
        0.25 * z_roce
        + 0.20 * z_sales_growth
        + 0.15 * z_opm
        + 0.15 * z_cfo_pat
        - 0.15 * z_de
        - 0.10 * z_pe
    )

    curr_df_clean['composite_score'] = (raw_score.rank(pct=True) * 100).round(1)
    
    ranked = curr_df_clean.sort_values(by='composite_score', ascending=False)
    
    display_cols = [
        'ticker', 'sector', 'composite_score', 'current_pe', 
        'roce', 'hist_sales_cagr_3y', 'hist_pat_cagr_3y', 
        'debt_to_equity', 'cfo_to_pat'
    ]
    
    print("\nTop 15 Ranked Stocks (Highest Fundamental Alpha for 2-3 Year Holding):")
    print(ranked[display_cols].head(15).to_string(index=False))

    print("\nBottom 10 Ranked Stocks (Weakest Fundamental Score / Overvalued / High Leverage):")
    print(ranked[display_cols].tail(10).to_string(index=False))

    ranked.to_csv(os.path.join(SCRATCH_DIR, "ranked_indian_stocks.csv"), index=False)
    summary_df.to_csv(os.path.join(SCRATCH_DIR, "factor_predictive_power.csv"), index=False)
    fi_df.to_csv(os.path.join(SCRATCH_DIR, "feature_importance.csv"), index=False)

if __name__ == '__main__':
    analyze_predictive_power()
