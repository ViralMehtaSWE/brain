#!/usr/bin/env python3
"""
Test whether the Fundamental Alpha Model weights outperform
in the NIFTY NEXT 50 Universe.
"""

import os
import sys
import re
import json
import time
import urllib.request
import urllib.error
import numpy as np
import pandas as pd

try:
    from config import CACHE_DIR, DATA_DIR
    SCRATCH_DIR = DATA_DIR
except ImportError:
    SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
    CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

# 24 Prominent Nifty Next 50 Companies across diversified sectors
NIFTY_NEXT_50 = [
    # Industrials, Capital Goods & Defense
    {"ticker": "BEL", "sector": "Industrials"},
    {"ticker": "HAL", "sector": "Industrials"},
    {"ticker": "SIEMENS", "sector": "Industrials"},
    {"ticker": "ABB", "sector": "Industrials"},
    {"ticker": "HAVELLS", "sector": "Industrials"},
    {"ticker": "POLYCAB", "sector": "Industrials"},
    {"ticker": "BHARATFORG", "sector": "Industrials"},
    
    # Consumer & Retail
    {"ticker": "PIDILITIND", "sector": "Materials"},
    {"ticker": "DABUR", "sector": "Consumer"},
    {"ticker": "MARICO", "sector": "Consumer"},
    {"ticker": "BERGEPAINT", "sector": "Consumer"},
    {"ticker": "TRENT", "sector": "Consumer"},
    {"ticker": "GODREJCP", "sector": "Consumer"},
    
    # Financial Services
    {"ticker": "CHOLAFIN", "sector": "Financials"},
    {"ticker": "SHRIRAMFIN", "sector": "Financials"},
    {"ticker": "RECLTD", "sector": "Financials"},
    {"ticker": "PFC", "sector": "Financials"},
    
    # Auto & Auto Ancillary
    {"ticker": "TVSMOTOR", "sector": "Auto"},
    {"ticker": "MOTHERSON", "sector": "Auto"},
    
    # Healthcare & Pharma
    {"ticker": "TORNTPHARM", "sector": "Healthcare"},
    {"ticker": "LUPIN", "sector": "Healthcare"},
    {"ticker": "AUROPHARMA", "sector": "Healthcare"},
    
    # Materials & Energy
    {"ticker": "JINDALSTEL", "sector": "Materials"},
    {"ticker": "GAIL", "sector": "Energy"}
]

def clean_num(val_str):
    if val_str is None: return np.nan
    s = str(val_str).replace('%', '').replace(',', '').strip()
    if s in ['', '-', 'None', 'N/A']: return np.nan
    try: return float(s)
    except: return np.nan

def fetch_single(ticker: str) -> str:
    cache_file = os.path.join(CACHE_DIR, f"{ticker}.html")
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            c = f.read()
            if len(c) > 5000: return c

    clean_t = ticker.upper()
    for suffix in ["/consolidated/", "/"]:
        url = f"https://www.screener.in/company/{clean_t}{suffix}"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    html = resp.read().decode('utf-8')
                    if len(html) > 5000:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            f.write(html)
                        time.sleep(2.0)
                        return html
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(6)
            continue
        except Exception:
            continue
    time.sleep(2.0)
    return ""

def parse_company_data(ticker: str, sector: str):
    html = fetch_single(ticker)
    if not html or len(html) < 5000:
        return None

    # Top ratios
    ratios = {}
    for m in re.finditer(r'<span class=\"name\">\s*([^<]+?)\s*</span>\s*<span class=\"nowrap value\">\s*₹?\s*<span class=\"number\">([^<]+)</span>', html):
        ratios[m.group(1).strip()] = clean_num(m.group(2))

    # Compound tables (3Y Stock Price CAGR, Sales CAGR)
    compound = {}
    for m in re.finditer(r'<table[^>]+class=\"ranges-table\"[^>]*>(.*?)</table>', html, re.DOTALL):
        th = re.search(r'<th[^>]*>(.*?)</th>', m.group(1), re.DOTALL)
        if th:
            title = re.sub(r'<[^>]+>', '', th.group(1)).strip()
            for term, val in re.findall(r'<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>', m.group(1), re.DOTALL):
                compound[f"{title}_{term.replace(':', '').strip()}"] = clean_num(val)

    # Statements
    def parse_last_col(sec_id):
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

    pl = parse_last_col('profit-loss')
    bs = parse_last_col('balance-sheet')
    cf = parse_last_col('cash-flow')
    rt = parse_last_col('ratios')

    pat = pl.get('Net Profit', np.nan)
    cfo = cf.get('Cash from Operating Activity', np.nan)
    net_worth = (bs.get('Equity Capital', 0) or 0) + (bs.get('Reserves', 0) or 0)
    borrowings = bs.get('Borrowings', 0) or 0

    return {
        'ticker': ticker,
        'sector': sector,
        'roce': ratios.get('ROCE', rt.get('ROCE %', np.nan)),
        'current_pe': ratios.get('Stock P/E', np.nan),
        'hist_sales_cagr_3y': compound.get('Compounded Sales Growth_3 Years', np.nan),
        'hist_pat_cagr_3y': compound.get('Compounded Profit Growth_3 Years', np.nan),
        'stock_price_cagr_3y': compound.get('Stock Price CAGR_3 Years', np.nan),
        'opm': pl.get('OPM %', np.nan),
        'debt_to_equity': (borrowings / net_worth) if net_worth > 0 else 0.0,
        'cfo_to_pat': (cfo / pat) if (cfo is not None and pat and pat > 0) else 1.0
    }

print("Fetching and analyzing Nifty Next 50 universe...")
records = []
for item in NIFTY_NEXT_50:
    t = item['ticker']
    sec = item['sector']
    d = parse_company_data(t, sec)
    if d:
        records.append(d)
        print(f"  Processed {t} | ROCE: {d['roce']}% | 3Y Stock Return: {d['stock_price_cagr_3y']}%")

df = pd.DataFrame(records)
print(f"\nSuccessfully parsed {len(df)} Nifty Next 50 companies.")
df.to_csv(os.path.join(SCRATCH_DIR, "nifty_next_50_df.csv"), index=False)
