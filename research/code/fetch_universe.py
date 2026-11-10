#!/usr/bin/env python3
import os
import sys
import re
import json
import time
import urllib.request
import urllib.error

CACHE_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch/screener_cache"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9'
}

UNIVERSE = [
    # IT Services
    {"ticker": "TCS", "sector": "IT"},
    {"ticker": "INFY", "sector": "IT"},
    {"ticker": "HCLTECH", "sector": "IT"},
    {"ticker": "WIPRO", "sector": "IT"},
    {"ticker": "TECHM", "sector": "IT"},
    
    # Financials
    {"ticker": "KOTAKBANK", "sector": "Financials"},
    {"ticker": "HDFCBANK", "sector": "Financials"},
    {"ticker": "ICICIBANK", "sector": "Financials"},
    {"ticker": "SBIN", "sector": "Financials"},
    {"ticker": "BAJFINANCE", "sector": "Financials"},
    
    # FMCG & Consumer
    {"ticker": "ITC", "sector": "Consumer"},
    {"ticker": "HINDUNILVR", "sector": "Consumer"},
    {"ticker": "NESTLEIND", "sector": "Consumer"},
    {"ticker": "BRITANNIA", "sector": "Consumer"},
    {"ticker": "TITAN", "sector": "Consumer"},
    
    # Automobile
    {"ticker": "MARUTI", "sector": "Auto"},
    {"ticker": "M&M", "sector": "Auto"},
    {"ticker": "BAJAJ-AUTO", "sector": "Auto"},
    {"ticker": "EICHERMOT", "sector": "Auto"},
    {"ticker": "TATAMOTORS", "sector": "Auto"},
    
    # Healthcare
    {"ticker": "SUNPHARMA", "sector": "Healthcare"},
    {"ticker": "CIPLA", "sector": "Healthcare"},
    {"ticker": "DRREDDY", "sector": "Healthcare"},
    {"ticker": "DIVISLAB", "sector": "Healthcare"},
    
    # Energy, Infra & Industrials
    {"ticker": "RELIANCE", "sector": "Energy"},
    {"ticker": "LT", "sector": "Industrials"},
    {"ticker": "NTPC", "sector": "Energy"},
    {"ticker": "ONGC", "sector": "Energy"},
    {"ticker": "TATASTEEL", "sector": "Materials"}
]

def fetch_single(url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status == 200:
                    return resp.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = (attempt + 1) * 6
                print(f"  [429 Rate Limit] Backing off for {wait_time}s on {url}...")
                time.sleep(wait_time)
            elif e.code == 404:
                return ""
            else:
                time.sleep(2)
        except Exception as e:
            time.sleep(2)
    return ""

def get_company_html(ticker: str) -> str:
    cache_file = os.path.join(CACHE_DIR, f"{ticker}.html")
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            content = f.read()
            if len(content) > 10000:
                print(f"[CACHED] {ticker} ({len(content)} bytes)")
                return content

    clean_t = ticker.upper()
    url_cons = f"https://www.screener.in/company/{clean_t}/consolidated/"
    html = fetch_single(url_cons)
    if not html or len(html) < 5000:
        time.sleep(1.5)
        url_std = f"https://www.screener.in/company/{clean_t}/"
        html = fetch_single(url_std)

    if html and len(html) > 5000:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[FETCHED] {ticker} ({len(html)} bytes)")
    else:
        print(f"[FAILED] {ticker}")

    time.sleep(2.5)
    return html

print(f"Processing universe of {len(UNIVERSE)} companies...")
for item in UNIVERSE:
    get_company_html(item['ticker'])
print("Done fetching universe!")
