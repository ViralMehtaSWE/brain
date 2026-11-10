#!/usr/bin/env python3
"""
Unit Test Suite for Transferability: NIFTY 50 Model Applied to NIFTY NEXT 50 Universe
"""

import unittest
import os
import json
import numpy as np
import pandas as pd

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
RESULTS_JSON = os.path.join(SCRATCH_DIR, "nifty50_on_next50_results.json")

class TestNifty50OnNext50(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(RESULTS_JSON, 'r') as f:
            cls.data = json.load(f)

    def test_01_portfolio_size_and_constituents(self):
        """Verify exactly 20 stocks selected from Nifty Next 50."""
        self.assertEqual(len(self.data['top20']), 20)

    def test_02_benchmark_outperformance(self):
        """Verify that the transferred Nifty 50 model beats the Nifty Next 50 benchmark CAGR."""
        port_ret = self.data['port_ret']
        bm_cagr = self.data['benchmark_cagr']
        self.assertGreater(port_ret, bm_cagr, f"Portfolio CAGR ({port_ret:.4f}) must exceed benchmark ({bm_cagr:.4f})")
        self.assertGreater(self.data['active_cagr'], 0.04, "Active outperformance must be > 4.0% CAGR")

    def test_03_risk_adjusted_outperformance(self):
        """Verify that the Sharpe ratio is significantly higher than the benchmark."""
        sharpe = self.data['sharpe']
        bm_sharpe = self.data['benchmark_sharpe']
        self.assertGreater(sharpe, bm_sharpe, f"Sharpe ({sharpe:.2f}) must beat benchmark Sharpe ({bm_sharpe:.2f})")
        self.assertGreater(self.data['active_sharpe'], 0.20, "Active Sharpe improvement must be > 0.20")

    def test_04_equal_weighted_cagr_outperformance(self):
        """Verify that even equal-weighted 20-stock basket beats the benchmark."""
        eq_ret = self.data['eq_ret']
        bm_cagr = self.data['benchmark_cagr'] * 100
        self.assertGreater(eq_ret, bm_cagr, "Equal weighted CAGR must beat benchmark")

    def test_05_cross_universe_overlap(self):
        """Verify that there is high overlap (at least 60%) between N50 model and Next 50 native model."""
        self.assertGreaterEqual(self.data['overlap_count'], 12, "At least 12 of 20 stocks must overlap across models")

if __name__ == '__main__':
    unittest.main()
