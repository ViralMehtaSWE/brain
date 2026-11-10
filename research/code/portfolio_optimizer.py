#!/usr/bin/env python3
"""
Fundamental Alpha & Risk-Adjusted Portfolio Construction Engine
Input: List of Indian companies + integer K
Output: Top K best fundamental companies and optimal capital allocations (money invested)
        that maximize risk-adjusted returns (Maximum Sharpe Ratio).
"""

import os
import sys
import re
import json
import urllib.request
import urllib.error
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import List, Dict, Any, Optional

try:
    from config import CACHE_DIR, PRICES_DIR, UNIVERSE_CSV
except ImportError:
    SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
    CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/html'
}

DEFAULT_SECTORS = {
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


class PortfolioOptimizer:
    """
    Constructs an optimal risk-adjusted portfolio by combining 
    Fundamental Multi-Factor Alpha with Modern Portfolio Theory (Mean-Variance / Max Sharpe).
    """

    def __init__(self, risk_free_rate: float = 0.07, default_capital: float = 1_000_000.0):
        """
        :param risk_free_rate: Annualized risk-free rate (default 7.0% for Indian 10Y G-Sec / Repo).
        :param default_capital: Total portfolio money to allocate (in INR ₹).
        """
        self.risk_free_rate = risk_free_rate
        self.default_capital = default_capital
        os.makedirs(CACHE_DIR, exist_ok=True)

    def clean_num(self, val_str) -> float:
        if val_str is None:
            return np.nan
        s = str(val_str).replace('%', '').replace(',', '').strip()
        if s in ['', '-', 'None', 'N/A']:
            return np.nan
        try:
            return float(s)
        except ValueError:
            return np.nan

    def get_company_id(self, ticker: str, html: str) -> Optional[str]:
        """Extract Screener internal company ID for chart/pricing APIs."""
        m = re.search(r'data-row-company-id=\"(\d+)\"', html)
        if not m:
            m = re.search(r'/api/company/(\d+)/', html)
        return m.group(1) if m else None

    def fetch_company_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Loads cached HTML or fetches fundamental data from Screener.in."""
        clean_t = ticker.upper().strip()
        cache_file = os.path.join(CACHE_DIR, f"{clean_t}.html")
        html = ""

        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                html = f.read()

        if len(html) < 5000:
            for suffix in ["/consolidated/", "/"]:
                url = f"https://www.screener.in/company/{clean_t}{suffix}"
                try:
                    req = urllib.request.Request(url, headers=HEADERS)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        if resp.status == 200:
                            html = resp.read().decode('utf-8')
                            with open(cache_file, "w", encoding="utf-8") as f:
                                f.write(html)
                            break
                except Exception:
                    continue

        if len(html) < 5000:
            return {"ticker": clean_t, "error": f"Failed to retrieve data for {clean_t}"}

        # 1. Company ID
        cid = self.get_company_id(clean_t, html)

        # 2. Key Ratios (Top Box)
        ratios = {}
        for m in re.finditer(r'<span class=\"name\">\s*([^<]+?)\s*</span>\s*<span class=\"nowrap value\">\s*₹?\s*<span class=\"number\">([^<]+)</span>', html):
            name = m.group(1).strip()
            ratios[name] = self.clean_num(m.group(2))

        # 3. Compound growth tables
        compound = {}
        for m in re.finditer(r'<table[^>]+class=\"ranges-table\"[^>]*>(.*?)</table>', html, re.DOTALL):
            th_match = re.search(r'<th[^>]*>(.*?)</th>', m.group(1), re.DOTALL)
            if th_match:
                title = re.sub(r'<[^>]+>', '', th_match.group(1)).strip()
                rows = re.findall(r'<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>', m.group(1), re.DOTALL)
                for term, val in rows:
                    term_clean = term.replace(':', '').strip()
                    compound[f"{title}_{term_clean}"] = self.clean_num(val)

        # 4. Financial Statements (P&L, Balance Sheet, Cash Flow)
        def parse_table_last_col(sec_id):
            pos = html.find(f'id="{sec_id}"')
            if pos == -1: return {}
            end = html.find('</section>', pos)
            sec_html = html[pos:end]
            tbody = re.search(r'<tbody>(.*?)</tbody>', sec_html, re.DOTALL)
            res = {}
            if tbody:
                for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', tbody.group(1), re.DOTALL):
                    tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
                    clean_tds = [self.clean_num(re.sub(r'<[^>]+>', '', td)) for td in tds]
                    if len(clean_tds) > 1:
                        raw_name = re.sub(r'<[^>]+>', '', tds[0]).replace('&nbsp;', ' ').replace('+', '').strip()
                        name = ' '.join(raw_name.split())
                        # Take latest non-nan column
                        vals = [v for v in clean_tds[1:] if pd.notnull(v)]
                        res[name] = vals[-1] if vals else np.nan
            return res

        pl_last = parse_table_last_col('profit-loss')
        bs_last = parse_table_last_col('balance-sheet')
        cf_last = parse_table_last_col('cash-flow')
        rt_last = parse_table_last_col('ratios')

        sales = pl_last.get('Sales', np.nan)
        pat = pl_last.get('Net Profit', np.nan)
        opm = pl_last.get('OPM %', np.nan)
        cfo = cf_last.get('Cash from Operating Activity', np.nan)
        
        borrowings = bs_last.get('Borrowings', 0) or 0
        net_worth = (bs_last.get('Equity Capital', 0) or 0) + (bs_last.get('Reserves', 0) or 0)
        debt_to_equity = (borrowings / net_worth) if net_worth > 0 else 0.0

        cfo_to_pat = (cfo / pat) if (cfo is not None and pat and pat > 0) else 1.0

        return {
            'ticker': clean_t,
            'company_id': cid,
            'sector': DEFAULT_SECTORS.get(clean_t, "General"),
            'roce': ratios.get('ROCE', rt_last.get('ROCE %', np.nan)),
            'current_pe': ratios.get('Stock P/E', np.nan),
            'hist_sales_cagr_3y': compound.get('Compounded Sales Growth_3 Years', np.nan),
            'hist_pat_cagr_3y': compound.get('Compounded Profit Growth_3 Years', np.nan),
            'opm': opm,
            'debt_to_equity': debt_to_equity,
            'cfo_to_pat': cfo_to_pat,
            'market_cap': ratios.get('Market Cap', np.nan)
        }

    def score_companies(self, company_list: List[str]) -> pd.DataFrame:
        """
        Calculates sector-neutral Z-scores and composite fundamental scores 
        for all input companies.
        """
        records = [self.fetch_company_fundamentals(t) for t in company_list]
        df = pd.DataFrame([r for r in records if "error" not in r])

        if df.empty:
            raise ValueError("No valid fundamental data could be retrieved for the provided tickers.")

        # Impute missing values with group medians
        df['roce'] = df['roce'].fillna(df['roce'].median())
        df['hist_sales_cagr_3y'] = df['hist_sales_cagr_3y'].fillna(df['hist_sales_cagr_3y'].median())
        df['opm'] = df['opm'].fillna(df['opm'].median())
        df['cfo_to_pat'] = df['cfo_to_pat'].fillna(1.0).clip(0, 3)
        df['debt_to_equity'] = df['debt_to_equity'].fillna(0.0).clip(0, 4)
        df['current_pe'] = df['current_pe'].fillna(df['current_pe'].median()).clip(5, 120)

        # Sector-Neutral Winsorized Z-Scores
        def z_score(series, sector):
            s_mean = series.groupby(sector).transform('mean')
            s_std = series.groupby(sector).transform('std').replace(0, 1).fillna(1)
            return (series - s_mean) / s_std

        z_roce = z_score(df['roce'], df['sector'])
        z_sales = z_score(df['hist_sales_cagr_3y'], df['sector'])
        z_opm = z_score(df['opm'], df['sector'])
        z_cfo = z_score(df['cfo_to_pat'], df['sector'])
        z_de = z_score(df['debt_to_equity'], df['sector'])
        z_pe = z_score(df['current_pe'], df['sector'])

        # Multi-Factor Formula
        raw_score = (
            0.25 * z_roce
            + 0.20 * z_sales
            + 0.15 * z_opm
            + 0.15 * z_cfo
            - 0.15 * z_de
            - 0.10 * z_pe
        )

        df['fundamental_score'] = (raw_score.rank(pct=True) * 100).round(1)
        return df.sort_values(by='fundamental_score', ascending=False).reset_index(drop=True)

    def fetch_price_series(self, ticker: str, company_id: Optional[str]) -> Optional[pd.Series]:
        """Retrieves 3-year historical closing price series directly from Screener.in."""
        clean_t = ticker.upper().strip()
        price_cache = os.path.join(CACHE_DIR, f"{clean_t}_price.csv")

        if os.path.exists(price_cache):
            df = pd.read_csv(price_cache, parse_dates=['date'])
            return df.set_index('date')['price']

        if not company_id:
            return None

        url = f"https://www.screener.in/api/company/{company_id}/chart/?q=Price-DMA50-DMA200-Volume&days=1095"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for ds in data.get('datasets', []):
                    if ds.get('metric') == 'Price':
                        df = pd.DataFrame(ds['values'], columns=['date', 'price'])
                        df['price'] = pd.to_numeric(df['price'], errors='coerce')
                        df['date'] = pd.to_datetime(df['date'])
                        df = df.dropna().drop_duplicates(subset=['date']).sort_values('date')
                        df.to_csv(price_cache, index=False)
                        return df.set_index('date')['price']
        except Exception:
            pass
        return None

    def optimize_maximum_sharpe(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        min_weight: float = 0.05,
        max_weight: float = 0.40
    ) -> np.ndarray:
        """
        Solves the Modern Portfolio Theory Tangency Portfolio:
            maximize Sharpe Ratio = (w^T mu - r_f) / sqrt(w^T Sigma w)
        subject to:
            sum(w) = 1.0,  min_weight <= w_i <= max_weight
        """
        n = len(expected_returns)
        # Ensure bounds are mathematically feasible
        if n * min_weight > 1.0:
            min_weight = 0.0
        if max_weight * n < 1.0:
            max_weight = 1.0 / n

        init_weights = np.ones(n) / n
        bounds = tuple((min_weight, max_weight) for _ in range(n))
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})

        def neg_sharpe(w):
            p_ret = np.dot(w, expected_returns)
            p_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
            if p_vol <= 1e-6:
                return 0.0
            return -(p_ret - self.risk_free_rate) / p_vol

        res = minimize(
            neg_sharpe,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'ftol': 1e-9, 'maxiter': 500}
        )

        if res.success:
            return np.maximum(0, res.x) / np.sum(np.maximum(0, res.x))
        else:
            # Fallback to inverse volatility if solver stalls
            diag_vols = np.sqrt(np.diag(cov_matrix))
            inv_vols = 1.0 / np.where(diag_vols > 0, diag_vols, 1.0)
            return inv_vols / np.sum(inv_vols)

    def optimize_risk_parity(self, cov_matrix: np.ndarray, min_weight: float = 0.01, max_weight: float = 0.35) -> np.ndarray:
        """
        Equal Risk Contribution (Risk-Parity) Optimizer:
        Allocates weights such that each asset contributes equally to total portfolio variance.
        Objective: minimize sum_i sum_j (w_i * (Sigma w)_i - w_j * (Sigma w)_j)^2
        """
        n = cov_matrix.shape[0]
        init_weights = np.ones(n) / n
        bounds = tuple((min_weight, max_weight) for _ in range(n))
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})

        def risk_parity_objective(w):
            p_var = np.dot(w.T, np.dot(cov_matrix, w))
            if p_var <= 1e-12:
                return 0.0
            mrc = np.dot(cov_matrix, w) # marginal risk contribution
            rc = w * mrc # risk contribution
            rc_target = p_var / n
            return np.sum((rc - rc_target) ** 2)

        res = minimize(
            risk_parity_objective,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'ftol': 1e-11, 'maxiter': 500}
        )
        if res.success:
            w = np.maximum(0, res.x)
            return w / np.sum(w)
        diag_vols = np.sqrt(np.diag(cov_matrix))
        inv_vols = 1.0 / np.where(diag_vols > 0, diag_vols, 1.0)
        return inv_vols / np.sum(inv_vols)

    def apply_turnover_and_costs(
        self,
        weights: np.ndarray,
        prior_weights: Optional[np.ndarray] = None,
        max_turnover: Optional[float] = None,
        cost_bps: float = 15.0
    ) -> Dict[str, Any]:
        """
        Enforces turnover constraint and deducts transaction costs (default 15 bps).
        Turnover = 0.5 * sum(|w - w_prior|)
        Cost = Turnover * (cost_bps / 10000.0)
        """
        if prior_weights is None:
            return {
                'weights': weights,
                'turnover': 0.0,
                'cost_deduction': 0.0
            }
        diff = np.abs(weights - prior_weights)
        raw_turnover = float(0.5 * np.sum(diff))
        if max_turnover is not None and raw_turnover > max_turnover:
            # Scale adjustment toward prior weights to satisfy turnover limit
            alpha = max_turnover / raw_turnover
            weights = prior_weights + alpha * (weights - prior_weights)
            weights = np.maximum(0, weights) / np.sum(np.maximum(0, weights))
            raw_turnover = float(0.5 * np.sum(np.abs(weights - prior_weights)))
        cost_deduction = float(raw_turnover * (cost_bps / 10000.0))
        return {
            'weights': weights,
            'turnover': raw_turnover,
            'cost_deduction': cost_deduction
        }


    def construct_portfolio(
        self,
        company_list: List[str],
        K: int,
        total_capital: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        End-to-End Orchestrator:
        1. Ranks all candidates using the Multi-Factor Fundamental Alpha Model.
        2. Selects the Top K companies.
        3. Retrieves 3-year historical price series and computes the covariance matrix.
        4. Calculates factor-implied expected returns (rewarding higher fundamental scores).
        5. Computes optimal weights maximizing the Sharpe Ratio.
        6. Allocates capital (INR ₹) to each company.
        """
        capital = total_capital if total_capital is not None else self.default_capital
        K = min(K, len(company_list))

        # 1. Rank universe on fundamentals
        scored_df = self.score_companies(company_list)
        top_k_df = scored_df.head(K).copy().reset_index(drop=True)
        top_tickers = top_k_df['ticker'].tolist()

        # 2. Get price series for covariance calculation
        price_dict = {}
        for _, row in top_k_df.iterrows():
            s = self.fetch_price_series(row['ticker'], row['company_id'])
            if s is not None and len(s) > 30:
                price_dict[row['ticker']] = s

        # Align prices into returns dataframe
        if len(price_dict) >= max(2, int(K * 0.6)):
            prices_df = pd.DataFrame(price_dict).dropna()
            returns_df = prices_df.pct_change().dropna()
            # Annualized covariance (using 52 weekly / 252 daily periods)
            annual_factor = 52.0 if len(returns_df) < 180 else 252.0
            cov_matrix = returns_df.cov().values * annual_factor
            ann_vols = returns_df.std().values * np.sqrt(annual_factor)
            available_tickers = list(returns_df.columns)
            top_k_df = top_k_df[top_k_df['ticker'].isin(available_tickers)].reset_index(drop=True)
        else:
            # Synthetic default covariance if price series unavailable
            available_tickers = top_tickers
            n = len(top_tickers)
            cov_matrix = np.eye(n) * (0.22 ** 2) + np.ones((n, n)) * 0.015
            ann_vols = np.full(n, 0.22)

        # 3. Factor-implied Expected Returns (Fundamental Alpha Anchoring)
        # Higher score = higher expected earnings compounding & alpha
        base_equity_premium = 0.08  # 8% equity risk premium above risk-free rate
        scores = top_k_df['fundamental_score'].values
        # Scale expected return from 12% to 22% based on fundamental percentile score
        expected_returns = self.risk_free_rate + base_equity_premium * (scores / 100.0 * 1.3)

        # 4. Maximize Sharpe Ratio
        weights = self.optimize_maximum_sharpe(
            expected_returns=expected_returns,
            cov_matrix=cov_matrix,
            min_weight=0.05,
            max_weight=min(0.35, 2.0 / len(top_k_df))
        )

        # 5. Portfolio Aggregate Metrics
        port_return = float(np.dot(weights, expected_returns))
        port_variance = float(np.dot(weights.T, np.dot(cov_matrix, weights)))
        port_volatility = float(np.sqrt(port_variance))
        port_sharpe = float((port_return - self.risk_free_rate) / port_volatility) if port_volatility > 0 else 0.0
        eff_constituents = float(1.0 / np.sum(weights ** 2))

        # 6. Build Output DataFrame
        allocations = []
        for i, row in top_k_df.iterrows():
            w = weights[i]
            allocated_money = w * capital
            allocations.append({
                'Ticker': row['ticker'],
                'Sector': row['sector'],
                'Fundamental Score (0-100)': row['fundamental_score'],
                'ROCE (%)': row['roce'],
                'P/E Ratio': row['current_pe'],
                'Expected Return (%)': round(expected_returns[i] * 100, 2),
                'Annual Volatility (%)': round(ann_vols[i] * 100, 2),
                'Optimal Weight (%)': round(w * 100, 2),
                'Money Invested (₹)': round(allocated_money, 2)
            })

        alloc_df = pd.DataFrame(allocations).sort_values(by='Optimal Weight (%)', ascending=False).reset_index(drop=True)

        return {
            'portfolio_summary': {
                'Total Capital (₹)': capital,
                'K Companies': len(top_k_df),
                'Expected Annual Return (%)': round(port_return * 100, 2),
                'Annual Portfolio Volatility (%)': round(port_volatility * 100, 2),
                'Risk-Adjusted Sharpe Ratio': round(port_sharpe, 3),
                'Effective Diversified Bets': round(eff_constituents, 1)
            },
            'allocations': alloc_df
        }


# ==============================================================================
# Example Demonstration
# ==============================================================================
if __name__ == '__main__':
    # Input candidate pool of 20 marquee Indian stocks
    candidate_pool = [
        "TCS", "INFY", "HCLTECH", "WIPRO", "NESTLEIND", "BRITANNIA", "ITC", 
        "TITAN", "BAJAJ-AUTO", "EICHERMOT", "MARUTI", "SUNPHARMA", "CIPLA", 
        "DIVISLAB", "RELIANCE", "ONGC", "NTPC", "LT", "TATASTEEL", "KOTAKBANK"
    ]

    K = 5
    invested_capital = 1_000_000.0  # ₹10,00,000 (10 Lakhs)

    optimizer = PortfolioOptimizer(risk_free_rate=0.07, default_capital=invested_capital)
    result = optimizer.construct_portfolio(candidate_pool, K=K, total_capital=invested_capital)

    print("=" * 90)
    print(f"OPTIMAL PORTFOLIO OF TOP K={K} BEST INDIAN COMPANIES (MAX RISK-ADJUSTED RETURNS)")
    print("=" * 90)
    for k, v in result['portfolio_summary'].items():
        print(f"  {k}: {v}")

    print("\nConstituents & Money Invested Breakdown:")
    print(result['allocations'].to_string(index=False))
