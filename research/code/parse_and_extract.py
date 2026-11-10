#!/usr/bin/env python3
"""
Empirical Predictive Power Analysis & Stock Scoring Engine on Indian Equities
Using Historical Fundamentals from Screener.in
"""

import os
import sys
import re
import json
import glob
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, ttest_1samp
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

CACHE_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch/screener_cache"

def clean_num(val_str):
    if val_str is None:
        return np.nan
    s = str(val_str).replace('%', '').replace(',', '').strip()
    if s in ['', '-', 'None']:
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan

def parse_financial_section(html: str, sec_id: str):
    pos = html.find(f'id="{sec_id}"')
    if pos == -1:
        return {}, []
    end = html.find('</section>', pos)
    sec_html = html[pos:end]

    thead = re.search(r'<thead>(.*?)</thead>', sec_html, re.DOTALL)
    periods = []
    if thead:
        for th in re.findall(r'<th[^>]*>(.*?)</th>', thead.group(1), re.DOTALL):
            c = re.sub(r'<[^>]+>', '', th).strip()
            if c and c != 'Raw PDF' and not c.startswith('+'):
                periods.append(c)

    tbody = re.search(r'<tbody>(.*?)</tbody>', sec_html, re.DOTALL)
    metrics = {}
    if tbody:
        for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', tbody.group(1), re.DOTALL):
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
            clean_tds = [re.sub(r'<[^>]+>', '', td).replace('&nbsp;', ' ').strip().replace(',', '') for td in tds]
            if len(clean_tds) > 1:
                name = ' '.join(clean_tds[0].replace('+', '').split())
                metrics[name] = [clean_num(x) for x in clean_tds[1:]]
    return metrics, periods

def parse_top_ratios(html: str):
    ratios = {}
    for m in re.finditer(r'<span class=\"name\">\s*([^<]+?)\s*</span>\s*<span class=\"nowrap value\">\s*₹?\s*<span class=\"number\">([^<]+)</span>', html):
        name = m.group(1).strip()
        val = clean_num(m.group(2))
        ratios[name] = val
    return ratios

def parse_compound_tables(html: str):
    data = {}
    for m in re.finditer(r'<table[^>]+class=\"ranges-table\"[^>]*>(.*?)</table>', html, re.DOTALL):
        th_match = re.search(r'<th[^>]*>(.*?)</th>', m.group(1), re.DOTALL)
        if not th_match:
            continue
        title = re.sub(r'<[^>]+>', '', th_match.group(1)).strip()
        rows = re.findall(r'<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>', m.group(1), re.DOTALL)
        for term, val in rows:
            term_clean = term.replace(':', '').strip()
            val_clean = clean_num(val)
            data[f"{title}_{term_clean}"] = val_clean
    return data

def extract_panel_data():
    """
    Parses all cached company HTMLs into:
    1. A longitudinal panel dataset of rolling periods (t predicting t+3)
    2. A current cross-section of the latest metrics for live scoring
    """
    files = glob.glob(os.path.join(CACHE_DIR, "*.html"))
    panel_records = []
    latest_records = []
    
    # Metadata map
    sector_map = {
        "TCS": "IT", "INFY": "IT", "HCLTECH": "IT", "WIPRO": "IT", "TECHM": "IT", "LTIM": "IT",
        "HDFCBANK": "Financials", "ICICIBANK": "Financials", "SBIN": "Financials", 
        "KOTAKBANK": "Financials", "AXISBANK": "Financials", "BAJFINANCE": "Financials",
        "MARUTI": "Auto", "TATAMOTORS": "Auto", "M&M": "Auto", "BAJAJ-AUTO": "Auto", "EICHERMOT": "Auto",
        "HINDUNILVR": "Consumer", "ITC": "Consumer", "NESTLEIND": "Consumer", 
        "BRITANNIA": "Consumer", "TITAN": "Consumer", "DABUR": "Consumer",
        "SUNPHARMA": "Healthcare", "CIPLA": "Healthcare", "DRREDDY": "Healthcare", 
        "DIVISLAB": "Healthcare", "APOLLOHOSP": "Healthcare",
        "RELIANCE": "Energy", "ONGC": "Energy", "NTPC": "Energy", "POWERGRID": "Energy", "COALINDIA": "Energy",
        "LT": "Industrials", "BEL": "Industrials", "SIEMENS": "Industrials", "ABB": "Industrials", "HAL": "Industrials",
        "TATASTEEL": "Materials", "JSWSTEEL": "Materials", "HINDALCO": "Materials", 
        "ULTRACEMCO": "Materials", "ASIANPAINT": "Consumer", "PIDILITIND": "Materials"
    }

    for fpath in files:
        ticker = os.path.splitext(os.path.basename(fpath))[0]
        with open(fpath, "r", encoding="utf-8") as f:
            html = f.read()

        if len(html) < 5000:
            continue

        sector = sector_map.get(ticker, "General")
        top_ratios = parse_top_ratios(html)
        compound = parse_compound_tables(html)
        pl, pl_periods = parse_financial_section(html, 'profit-loss')
        bs, bs_periods = parse_financial_section(html, 'balance-sheet')
        cf, cf_periods = parse_financial_section(html, 'cash-flow')
        rt, rt_periods = parse_financial_section(html, 'ratios')

        if not pl_periods or 'Sales' not in pl or 'Net Profit' not in pl:
            continue

        # Build year-indexed dictionaries
        pl_by_yr = {}
        for i, p in enumerate(pl_periods):
            pl_by_yr[p] = {k: v[i] if i < len(v) else np.nan for k, v in pl.items()}

        bs_by_yr = {}
        for i, p in enumerate(bs_periods):
            bs_by_yr[p] = {k: v[i] if i < len(v) else np.nan for k, v in bs.items()}

        cf_by_yr = {}
        for i, p in enumerate(cf_periods):
            cf_by_yr[p] = {k: v[i] if i < len(v) else np.nan for k, v in cf.items()}

        rt_by_yr = {}
        for i, p in enumerate(rt_periods):
            rt_by_yr[p] = {k: v[i] if i < len(v) else np.nan for k, v in rt.items()}

        # Filter standard March fiscal year periods (ignore TTM for panel alignment)
        fiscal_years = [p for p in pl_periods if re.match(r'Mar \d{4}', p)]
        
        # 1. Build Historical Rolling Observations (Predicting 3Y Forward Growth)
        # We need at least 3 years prior for historical growth and 3 years ahead for target
        # E.g., for t = 2018, historical is 2015->2018, target is 2018->2021
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

            # Features at time t
            sales_t = curr_pl.get('Sales', np.nan)
            sales_t_minus_3 = prev_pl.get('Sales', np.nan)
            pat_t = curr_pl.get('Net Profit', np.nan)
            pat_t_minus_3 = prev_pl.get('Net Profit', np.nan)
            eps_t = curr_pl.get('EPS in Rs', np.nan)
            opm_t = curr_pl.get('OPM %', np.nan)
            prev_opm = prev_pl.get('OPM %', np.nan)

            # Targets at time t + 3
            pat_t_plus_3 = fwd_pl.get('Net Profit', np.nan)
            eps_t_plus_3 = fwd_pl.get('EPS in Rs', np.nan)

            # Compute rates
            hist_sales_cagr = ((sales_t / sales_t_minus_3) ** (1/3) - 1) * 100 if (sales_t and sales_t_minus_3 and sales_t_minus_3 > 0 and sales_t > 0) else np.nan
            hist_pat_cagr = ((pat_t / pat_t_minus_3) ** (1/3) - 1) * 100 if (pat_t and pat_t_minus_3 and pat_t_minus_3 > 0 and pat_t > 0) else np.nan
            opm_expansion_3y = (opm_t - prev_opm) if (opm_t is not None and prev_opm is not None) else np.nan

            roce = curr_rt.get('ROCE %', np.nan)
            wc_days = curr_rt.get('Working Capital Days', np.nan)
            debtor_days = curr_rt.get('Debtor Days', np.nan)

            borrowings = curr_bs.get('Borrowings', np.nan)
            net_worth = (curr_bs.get('Equity Capital', 0) or 0) + (curr_bs.get('Reserves', 0) or 0)
            debt_to_equity = (borrowings / net_worth) if (net_worth and net_worth > 0 and borrowings is not None) else 0.0

            cfo = curr_cf.get('Cash from Operating Activity', np.nan)
            fcf = curr_cf.get('Free Cash Flow', np.nan)
            cfo_to_pat = (cfo / pat_t) if (cfo is not None and pat_t and pat_t > 0) else np.nan
            fcf_to_sales = (fcf / sales_t * 100) if (fcf is not None and sales_t and sales_t > 0) else np.nan

            # Forward Targets
            fwd_pat_cagr = ((pat_t_plus_3 / pat_t) ** (1/3) - 1) * 100 if (pat_t_plus_3 and pat_t and pat_t > 0 and pat_t_plus_3 > 0) else np.nan
            fwd_eps_cagr = ((eps_t_plus_3 / eps_t) ** (1/3) - 1) * 100 if (eps_t_plus_3 and eps_t and eps_t > 0 and eps_t_plus_3 > 0) else np.nan

            if pd.notnull(fwd_pat_cagr):
                panel_records.append({
                    'ticker': ticker,
                    'sector': sector,
                    'period': t_yr,
                    'hist_sales_cagr': hist_sales_cagr,
                    'hist_pat_cagr': hist_pat_cagr,
                    'opm': opm_t,
                    'opm_expansion_3y': opm_expansion_3y,
                    'roce': roce,
                    'debt_to_equity': debt_to_equity,
                    'cfo_to_pat': cfo_to_pat,
                    'fcf_to_sales': fcf_to_sales,
                    'wc_days': wc_days,
                    'debtor_days': debtor_days,
                    'fwd_pat_cagr_3y': fwd_pat_cagr,
                    'fwd_eps_cagr_3y': fwd_eps_cagr
                })

        # 2. Extract Latest Current Data for Live Scoring
        latest_yr = fiscal_years[-1] if fiscal_years else "TTM"
        curr_pl = pl_by_yr.get("TTM", pl_by_yr.get(latest_yr, {}))
        curr_bs = bs_by_yr.get(latest_yr, {})
        curr_cf = cf_by_yr.get(latest_yr, {})
        curr_rt = rt_by_yr.get(latest_yr, {})

        net_worth = (curr_bs.get('Equity Capital', 0) or 0) + (curr_bs.get('Reserves', 0) or 0)
        borrowings = curr_bs.get('Borrowings', 0)
        de = (borrowings / net_worth) if (net_worth and net_worth > 0) else 0.0

        sales = curr_pl.get('Sales', np.nan)
        pat = curr_pl.get('Net Profit', np.nan)
        cfo = curr_cf.get('Cash from Operating Activity', np.nan)
        fcf = curr_cf.get('Free Cash Flow', np.nan)

        latest_records.append({
            'ticker': ticker,
            'sector': sector,
            'current_pe': top_ratios.get('Stock P/E', np.nan),
            'roce': top_ratios.get('ROCE', curr_rt.get('ROCE %', np.nan)),
            'roe': top_ratios.get('ROE', compound.get('Return on Equity_3 Years', np.nan)),
            'hist_sales_cagr_3y': compound.get('Compounded Sales Growth_3 Years', np.nan),
            'hist_pat_cagr_3y': compound.get('Compounded Profit Growth_3 Years', np.nan),
            'stock_price_cagr_3y': compound.get('Stock Price CAGR_3 Years', np.nan),
            'opm': curr_pl.get('OPM %', np.nan),
            'debt_to_equity': de,
            'cfo_to_pat': (cfo / pat) if (cfo is not None and pat and pat > 0) else np.nan,
            'fcf_to_sales': (fcf / sales * 100) if (fcf is not None and sales and sales > 0) else np.nan,
            'wc_days': curr_rt.get('Working Capital Days', np.nan),
            'peg_ratio': (top_ratios.get('Stock P/E', np.nan) / compound.get('Compounded Profit Growth_3 Years', np.nan)) 
                         if (compound.get('Compounded Profit Growth_3 Years', 0) and compound.get('Compounded Profit Growth_3 Years', 0) > 0) else np.nan
        })

    return pd.DataFrame(panel_records), pd.DataFrame(latest_records)

if __name__ == '__main__':
    panel_df, current_df = extract_panel_data()
    print(f"Loaded {len(panel_df)} historical panel observations across {panel_df['ticker'].nunique()} Indian companies.")
    print(f"Loaded {len(current_df)} current company profiles.")
    
    panel_df.to_csv("/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch/panel_df.csv", index=False)
    current_df.to_csv("/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch/current_df.csv", index=False)
