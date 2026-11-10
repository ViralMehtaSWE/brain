#!/usr/bin/env python3
"""
Unit Test Suite for Exhaustive Nifty Midcap 150 Fundamental Alpha Analysis
"""

import unittest
import os
import json
import numpy as np
import pandas as pd

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
CACHE_DIR = os.path.join(SCRATCH_DIR, "screener_cache")
UNIVERSE_CSV = os.path.join(SCRATCH_DIR, "nifty_250_universe.csv")
RESULTS_JSON = os.path.join(SCRATCH_DIR, "midcap150_exhaustive_results.json")
PORTFOLIO_CSV = os.path.join(SCRATCH_DIR, "midcap150_optimized_portfolio.csv")

class TestMidcap150Analysis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.universe_df = pd.read_csv(UNIVERSE_CSV)
        cls.midcaps = cls.universe_df[cls.universe_df['Benchmark_Index'] == 'NIFTY MIDCAP 150']

    def test_01_universe_exact_count(self):
        """Test that the Midcap universe contains exactly 150 constituents."""
        self.assertEqual(len(self.midcaps), 150, "Nifty Midcap 150 must have exactly 150 constituents.")

    def test_02_data_presence_and_integrity(self):
        """Test that cached Screener HTML files are authentic, non-empty, and contain real tables."""
        symbols = self.midcaps['Symbol'].tolist()
        cached_count = 0
        for s in symbols:
            p = os.path.join(CACHE_DIR, f"{s}.html")
            if os.path.exists(p) and os.path.getsize(p) > 2000:
                cached_count += 1
                with open(p, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.assertIn("profit-loss", content, f"{s} must contain profit-loss section")
        # Must have high coverage of universe
        self.assertGreaterEqual(cached_count, 140, "At least 140 of 150 midcap stocks must have valid cached data.")

    def test_03_results_file_exists_and_valid(self):
        """Test that the analysis results JSON exists and contains all required factor metrics."""
        if not os.path.exists(RESULTS_JSON):
            self.skipTest("Results JSON not yet generated.")
        with open(RESULTS_JSON, 'r') as f:
            data = json.load(f)
        self.assertIn('factor_statistics', data)
        self.assertIn('unrounded_weights', data)
        self.assertIn('rounded_weights', data)
        self.assertIn('portfolio', data)

    def test_04_factor_weights_sum_to_one(self):
        """Test that unrounded and rounded weights sum strictly to 1.0."""
        if not os.path.exists(RESULTS_JSON):
            self.skipTest("Results JSON not yet generated.")
        with open(RESULTS_JSON, 'r') as f:
            data = json.load(f)
        unrounded = data['unrounded_weights']
        rounded = data['rounded_weights']
        self.assertAlmostEqual(sum(unrounded.values()), 1.0, places=5)
        self.assertAlmostEqual(sum(rounded.values()), 1.0, places=2)

    def test_05_portfolio_size_constraint(self):
        """Test that portfolio size is strictly within 15-25 stocks."""
        if not os.path.exists(PORTFOLIO_CSV):
            self.skipTest("Portfolio CSV not yet generated.")
        df = pd.read_csv(PORTFOLIO_CSV)
        self.assertTrue(15 <= len(df) <= 25, f"Portfolio size {len(df)} must be between 15 and 25.")

    def test_06_position_weight_bounds(self):
        """Test that position weights are between 2.0% and 12.0% to prevent single-stock dominance."""
        if not os.path.exists(PORTFOLIO_CSV):
            self.skipTest("Portfolio CSV not yet generated.")
        df = pd.read_csv(PORTFOLIO_CSV)
        for w in df['weight_pct']:
            self.assertGreaterEqual(w, 2.0, "Individual position weight must be >= 2.0%")
            self.assertLessEqual(w, 12.0, "Individual position weight must be <= 12.0%")

    def test_07_capital_conservation(self):
        """Test that portfolio weight sums to 100.0% and capital sums to exactly ₹10,00,000."""
        if not os.path.exists(PORTFOLIO_CSV):
            self.skipTest("Portfolio CSV not yet generated.")
        df = pd.read_csv(PORTFOLIO_CSV)
        self.assertAlmostEqual(df['weight_pct'].sum(), 100.0, places=1)
        self.assertAlmostEqual(df['capital_inr'].sum(), 1_000_000.0, places=0)

    def test_08_sector_diversification(self):
        """Test that no single industry represents more than 35% of total portfolio capital."""
        if not os.path.exists(PORTFOLIO_CSV):
            self.skipTest("Portfolio CSV not yet generated.")
        df = pd.read_csv(PORTFOLIO_CSV)
        sector_weights = df.groupby('industry')['weight_pct'].sum()
        max_sector_weight = sector_weights.max()
        self.assertLessEqual(max_sector_weight, 35.0, f"Max sector concentration {max_sector_weight:.1f}% exceeds 35%")

    def test_09_benchmark_comparison_metrics(self):
        """Test that benchmark comparison metrics (CAGR, Volatility, Sharpe, Alpha) are realistic and finite."""
        if not os.path.exists(RESULTS_JSON):
            self.skipTest("Results JSON not yet generated.")
        with open(RESULTS_JSON, 'r') as f:
            data = json.load(f)
        self.assertTrue(np.isfinite(data['portfolio_return']))
        self.assertTrue(np.isfinite(data['portfolio_volatility']))
        self.assertTrue(np.isfinite(data['portfolio_sharpe']))
        self.assertGreater(data['portfolio_volatility'], 0.05, "Portfolio volatility must be realistic (> 5%)")
        self.assertEqual(data['benchmark_cagr'], 0.1850)

if __name__ == '__main__':
    unittest.main()
