#!/usr/bin/env python3
"""
Forensic Price & CID Re-verification Script
1. Extracts the exact, authoritative company_id directly from each stock's cached HTML.
2. Compares the latest price in every *_price.csv against the 'Current Price' in the stock's HTML.
3. Re-fetches any price CSV that was fetched with an erroneous CID or whose price deviates from the verified current price.
"""

import os
import re
import json
import time
import urllib.request
import pandas as pd

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")
UNIVERSE_CSV = os.path.join(SCRATCH_DIR, "nifty_250_universe.csv")
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01'
}

def clean_num(val_str):
    if val_str is None: return None
    s = str(val_str).replace('%', '').replace(',', '').strip()
    if s in ['', '-', 'None']: return None
    try: return float(s)
    except: return None

def extract_meta_from_html(sym):
    clean_s = 'TATAMOTORS' if sym in ['TMPV', 'TMCV'] else sym
    fpath = os.path.join(CACHE_DIR, f"{clean_s}.html")
    if not os.path.exists(fpath): return None, None
    with open(fpath, "r", encoding="utf-8") as f:
        html = f.read()
    
    # 1. Company ID
    cid_m = re.search(r'data-row-company-id=\"(\d+)\"', html) or re.search(r'/api/company/(\d+)/', html)
    cid = cid_m.group(1) if cid_m else None
    
    # 2. Current Price from top box
    cp_match = re.search(r'Current Price.*?<span class=\"number\">([^<]+)</span>', html, re.DOTALL)
    curr_price = clean_num(cp_match.group(1)) if cp_match else None
    
    return cid, curr_price

def main():
    df_250 = pd.read_csv(UNIVERSE_CSV)
    print(f"Auditing all {len(df_250)} stocks in universe...")
    
    to_refetch = []
    
    for s in df_250['Symbol']:
        clean_s = 'TATAMOTORS' if s in ['TMPV', 'TMCV'] else s
        cid, curr_price = extract_meta_from_html(clean_s)
        p_csv = os.path.join(CACHE_DIR, f"{clean_s}_price.csv")
        
        if not os.path.exists(p_csv):
            if cid:
                to_refetch.append((clean_s, cid, curr_price, "File missing"))
            continue
            
        try:
            df_p = pd.read_csv(p_csv)
            if len(df_p) < 10:
                to_refetch.append((clean_s, cid, curr_price, "Too few records"))
                continue
            last_p = float(df_p['price'].iloc[-1])
            # If last price deviates by more than 20% from HTML current price, it was fetched with the WRONG CID!
            if curr_price and abs(last_p - curr_price) / curr_price > 0.20:
                to_refetch.append((clean_s, cid, curr_price, f"Price mismatch: CSV last={last_p}, HTML={curr_price}"))
        except Exception as e:
            to_refetch.append((clean_s, cid, curr_price, f"Read error: {e}"))
            
    print(f"\nFound {len(to_refetch)} price CSVs that need re-fetching:")
    for sym, cid, cp, reason in to_refetch:
        print(f"  {sym:<12} (CID: {cid:<8}, CurrPrice: {cp}): {reason}")
        
    print("\nRe-fetching correct price series directly from Screener chart API...")
    for sym, cid, cp, reason in to_refetch:
        if not cid:
            print(f"  [SKIP] {sym} (No CID)")
            continue
        url = f"https://www.screener.in/api/company/{cid}/chart/?q=Price-DMA50-DMA200-Volume&days=1095"
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    for ds in data.get('datasets', []):
                        if ds.get('metric') == 'Price':
                            df_new = pd.DataFrame(ds['values'], columns=['date', 'price'])
                            df_new = df_new.dropna().drop_duplicates('date')
                            p_csv = os.path.join(CACHE_DIR, f"{sym}_price.csv")
                            df_new.to_csv(p_csv, index=False)
                            new_last = df_new['price'].iloc[-1]
                            print(f"  [FIXED] {sym}: {len(df_new)} records, new_last={new_last} (HTML={cp})")
                            time.sleep(1.5)
                            break
                    break
            except Exception as e:
                print(f"  Attempt {attempt+1} failed for {sym}: {e}")
                time.sleep(3.0)

    print("\nForensic price audit & repair complete.")

if __name__ == '__main__':
    main()
