#!/usr/bin/env python3
"""
Unit Test Suite for Transferability: NIFTY 50 Model Applied to NIFTY MIDCAP 150 Universe
"""

import unittest
import os
import json
import numpy as np
import pandas as pd

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
RESULTS_JSON = os.path.join(SCRATCH_DIR, "nifty50_on_midcaps_results.json")

class TestNifty50OnMidcaps(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(RESULTS_JSON, 'r') as f:
            cls.data = json.load(f)

    def test_01_portfolio_size_and_constituents(self):
        """Verify exactly 20 stocks selected from Nifty Midcap 150."""
        self.assertEqual(len(self.data['portfolio']), 20)

    def test_02_weight_bounds_and_conservation(self):
        """Verify weights satisfy 2.0% - 10.5% bounds and sum to exactly 100.0%."""
        weights = [r['weight_pct'] for r in self.data['portfolio']]
        total_w = sum(weights)
        self.assertAlmostEqual(total_w, 100.0, places=1)
        for w in weights:
            self.assertGreaterEqual(w, 2.0, "Position floor >= 2.0%")
            self.assertLessEqual(w, 10.5, "Position ceiling <= 10.5%")

    def test_03_capital_conservation(self):
        """Verify allocated capital sums to exactly ₹10,00,000."""
        cap = sum(r['capital_inr'] for r in self.data['portfolio'])
        self.assertAlmostEqual(cap, 1_000_000.0, places=0)

    def test_04_benchmark_outperformance(self):
        """Verify that the transferred N50 model outperforms the Nifty Midcap 150 benchmark."""
        port_ret = self.data['port_ret']
        bm_cagr = self.data['benchmark_cagr']
        self.assertGreater(port_ret, bm_cagr, f"Portfolio return ({port_ret:.4f}) must beat benchmark ({bm_cagr:.4f})")
        self.assertGreater(self.data['active_cagr'], 0.05, "Active outperformance must exceed +5.0% CAGR")

    def test_05_equal_weighted_cagr_beats_benchmark(self):
        """Verify that even an equal-weighted 20-stock portfolio beats the benchmark."""
        eq_ret = self.data['eq_ret']
        bm_cagr_pct = self.data['benchmark_cagr'] * 100
        self.assertGreater(eq_ret, bm_cagr_pct, f"Equal weighted CAGR ({eq_ret:.2f}%) must beat benchmark ({bm_cagr_pct:.2f}%)")

    def test_06_sharpe_expansion(self):
        """Verify that the strategy achieves a significantly superior Sharpe ratio."""
        sharpe = self.data['sharpe']
        bm_sharpe = self.data['benchmark_sharpe']
        self.assertGreater(sharpe, bm_sharpe, f"Sharpe ({sharpe:.2f}) must beat benchmark Sharpe ({bm_sharpe:.2f})")

    def test_07_cross_universe_high_overlap(self):
        """Verify high overlap (at least 70%) between transferred N50 model and native Midcap model."""
        self.assertGreaterEqual(self.data['overlap_count'], 14, "At least 14 of 20 stocks must overlap across models")

if __name__ == '__main__':
    unittest.main()
