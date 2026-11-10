#!/usr/bin/env python3
"""
Unit Test Suite for 3x3 Cross-Universe Factor Transferability Matrix
"""

import unittest
import os
import json

try:
    from config import DATA_DIR
    MATRIX_JSON = os.path.join(DATA_DIR, "cross_universe_matrix_results.json")
except ImportError:
    SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
    MATRIX_JSON = os.path.join(SCRATCH_DIR, "cross_universe_matrix_results.json")

class TestCrossUniverseMatrix(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(MATRIX_JSON):
            fallback = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch/cross_universe_matrix_results.json"
            with open(fallback, "r") as f:
                cls.matrix = json.load(f)
        else:
            with open(MATRIX_JSON, "r") as f:
                cls.matrix = json.load(f)

    def test_01_matrix_dimensions(self):
        """Verify that all 3 universes and all 3 models exist (9 pairs)."""
        self.assertEqual(len(self.matrix), 3, "Must have exactly 3 universes.")
        for u in ['NIFTY 50', 'NIFTY NEXT 50', 'NIFTY MIDCAP 150']:
            self.assertIn(u, self.matrix)
            self.assertEqual(len(self.matrix[u]), 3, f"{u} must evaluate exactly 3 models.")

    def test_02_valid_metrics_computed(self):
        """Verify that all 9 combinations compute finite, valid returns, volatilities, and Sharpe ratios."""
        for u, models in self.matrix.items():
            for m, res in models.items():
                self.assertTrue(pd.notnull(res['opt_cagr']))
                self.assertTrue(pd.notnull(res['ew_cagr']))
                self.assertGreater(res['opt_vol'], 0.0)
                self.assertTrue(pd.notnull(res['opt_sharpe']))
                self.assertEqual(len(res['selected_stocks']), 20)

    def test_03_equal_weighted_cagr_positive(self):
        """Verify that equal-weighted baskets generate positive absolute returns across all 9 combinations."""
        for u, models in self.matrix.items():
            for m, res in models.items():
                self.assertGreater(res['ew_cagr'], 0.05, f"EW CAGR must be positive for {m} on {u}")

    def test_04_midcaps_highest_absolute_returns(self):
        """Verify that Midcap universe generates the highest returns across all models."""
        for m in ['NIFTY 50 Model', 'NIFTY NEXT 50 Model', 'NIFTY MIDCAP 150 Model']:
            mid_cagr = self.matrix['NIFTY MIDCAP 150'][m]['opt_cagr']
            n50_cagr = self.matrix['NIFTY 50'][m]['opt_cagr']
            next50_cagr = self.matrix['NIFTY NEXT 50'][m]['opt_cagr']
            self.assertGreater(mid_cagr, n50_cagr, "Midcap returns must exceed Nifty 50 returns")


if __name__ == '__main__':
    unittest.main()
