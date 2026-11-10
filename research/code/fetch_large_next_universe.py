#!/usr/bin/env python3
"""
Polite batch fetcher for missing Nifty 50 and Nifty Next 50 stocks.
Stores HTML files into screener_cache.
"""

import urllib.request
import urllib.error
import time
import os
import pandas as pd

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

df_250 = pd.read_csv(os.path.join(SCRATCH_DIR, "nifty_250_universe.csv"))
target_symbols = df_250[df_250['Benchmark_Index'].isin(['NIFTY 50', 'NIFTY NEXT 50'])]['Symbol'].tolist()

def fetch_stock(ticker):
    clean_t = ticker.upper()
    cache_f = os.path.join(CACHE_DIR, f"{clean_t}.html")
    if os.path.exists(cache_f):
        with open(cache_f, "r", encoding="utf-8") as f:
            if len(f.read()) > 5000: return True

    for suffix in ["/consolidated/", "/"]:
        url = f"https://www.screener.in/company/{clean_t}{suffix}"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    html = resp.read().decode('utf-8')
                    if len(html) > 5000:
                        with open(cache_f, "w", encoding="utf-8") as f:
                            f.write(html)
                        print(f"[OK] {clean_t}")
                        time.sleep(2.0)
                        return True
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"  [429] Backing off 6s on {clean_t}...")
                time.sleep(6.0)
            continue
        except Exception:
            continue
    time.sleep(2.0)
    return False

print(f"Processing target list of {len(target_symbols)} symbols...")
for s in target_symbols:
    fetch_stock(s)
print("Finished batch fetch.")
