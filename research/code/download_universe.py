#!/usr/bin/env python3
"""
Downloads and consolidates the official constituent lists for:
  - NIFTY 50 (50 stocks)
  - NIFTY NEXT 50 (50 stocks)
  - NIFTY MIDCAP 150 (150 stocks)
Total: 250 stocks across 19 sectors.
"""

import urllib.request
import io
import os
import pandas as pd

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

URLS = {
    'NIFTY 50': 'https://archives.nseindia.com/content/indices/ind_nifty50list.csv',
    'NIFTY NEXT 50': 'https://archives.nseindia.com/content/indices/ind_niftynext50list.csv',
    'NIFTY MIDCAP 150': 'https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv'
}

def load_official_universe():
    dfs = []
    for index_name, url in URLS.items():
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(content))
            df['Benchmark_Index'] = index_name
            dfs.append(df)
            print(f"Loaded {len(df)} stocks from {index_name}")

    consolidated = pd.concat(dfs, ignore_index=True)
    out_path = os.path.join(SCRATCH_DIR, "nifty_250_universe.csv")
    consolidated.to_csv(out_path, index=False)
    print(f"Saved complete universe of {len(consolidated)} stocks to {out_path}")
    return consolidated

if __name__ == '__main__':
    load_official_universe()
