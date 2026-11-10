#!/usr/bin/env python3
"""
Fetch the 17 missing daily price history files from Screener.in
"""

import urllib.request
import json
import time
import os
import pandas as pd

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01'
}

needed = {
    'HDFCLIFE': '1273934',
    'GRASIM': '1183',
    'MARUTI': '1961',
    'DRREDDY': '913',
    'MAXHEALTH': '1274191',
    'GODREJCP': '1161',
    'JINDALSTEL': '1551',
    'TORNTPHARM': '3049',
    'DLF': '902',
    'IOC': '1440',
    'VAML': '1274530',
    'ICICIGI': '1273823',
    'MARICO': '1954',
    'HEROMOTOCO': '1238',
    'JUBLFOOD': '1576',
    'HEXT': '1274516',
    'BHARTIHEXA': '1274640'
}

print(f"Fetching {len(needed)} price files...")
for sym, cid in needed.items():
    p_f = os.path.join(CACHE_DIR, f"{sym}_price.csv")
    if os.path.exists(p_f) and os.path.getsize(p_f) > 100:
        print(f"[EXISTS] {sym}")
        continue
        
    url = f"https://www.screener.in/api/company/{cid}/chart/?q=Price-DMA50-DMA200-Volume&days=1095"
    success = False
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for ds in data.get('datasets', []):
                    if ds.get('metric') == 'Price':
                        df = pd.DataFrame(ds['values'], columns=['date', 'price'])
                        df.dropna().drop_duplicates('date').to_csv(p_f, index=False)
                        print(f"[OK] {sym} ({len(df)} prices)")
                        success = True
                        break
            if success:
                time.sleep(2.0)
                break
        except Exception as e:
            print(f"  Attempt {attempt+1} failed for {sym}: {e}")
            time.sleep(4.0)

print("Done fetching price files.")
