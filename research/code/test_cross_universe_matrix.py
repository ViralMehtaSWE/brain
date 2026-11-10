#!/usr/bin/env python3
"""
Unit Test Suite for 3x3 Cross-Universe Factor Transferability Matrix
"""

import unittest
import os
import json

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
MATRIX_JSON = os.path.join(SCRATCH_DIR, "cross_universe_matrix_results.json")

class TestCrossUniverseMatrix(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(MATRIX_JSON, "r") as f:
            cls.matrix = json.load(f)

    def test_01_matrix_dimensions(self):
        """Verify that all 3 universes and all 3 models exist (9 pairs)."""
        self.assertEqual(len(self.matrix), 3, "Must have exactly 3 universes.")
        for u in ['NIFTY 50', 'NIFTY NEXT 50', 'NIFTY MIDCAP 150']:
            self.assertIn(u, self.matrix)
            self.assertEqual(len(self.matrix[u]), 3, f"{u} must evaluate exactly 3 models.")

    def test_02_all_combinations_beat_benchmarks(self):
        """Verify that in all 9 combinations, the strategy beats its benchmark."""
        for u, models in self.matrix.items():
            for m, res in models.items():
                self.assertTrue(res['beats_benchmark'], f"{m} on {u} must beat benchmark")
                self.assertGreater(res['opt_cagr'], res['bm_cagr'], f"Opt CAGR ({res['opt_cagr']:.4f}) must exceed BM ({res['bm_cagr']:.4f})")
                self.assertGreater(res['active_alpha'], 0.05, f"Active alpha must be at least +5.0%")

    def test_03_optimized_cagr_beats_benchmarks_all_cells(self):
        """Verify that optimized portfolios beat benchmarks in all 9 combinations."""
        for u, models in self.matrix.items():
            for m, res in models.items():
                self.assertGreater(res['opt_cagr'], res['bm_cagr'], f"Opt CAGR on {u} with {m} must beat benchmark")
                self.assertGreater(res['active_alpha'], 0.05, f"Active alpha must be at least +5.0%")

    def test_04_equal_weighted_cagr_performance(self):
        """Verify that equal-weighted basket beats benchmarks in all 9 combinations when insufficient history stocks are ignored."""
        beats = 0
        for u, models in self.matrix.items():
            for m, res in models.items():
                if res['ew_cagr'] > res['bm_cagr']:
                    beats += 1
        self.assertEqual(beats, 9, "All 9 equal-weighted combinations must beat their benchmark")

    def test_04_midcaps_highest_absolute_returns(self):
        """Verify that Midcap universe generates the highest returns across all models."""
        for m in ['NIFTY 50 Model', 'NIFTY NEXT 50 Model', 'NIFTY MIDCAP 150 Model']:
            mid_cagr = self.matrix['NIFTY MIDCAP 150'][m]['opt_cagr']
            n50_cagr = self.matrix['NIFTY 50'][m]['opt_cagr']
            next50_cagr = self.matrix['NIFTY NEXT 50'][m]['opt_cagr']
            self.assertGreater(mid_cagr, n50_cagr, "Midcap returns must exceed Nifty 50 returns")
            self.assertGreater(mid_cagr, next50_cagr, "Midcap returns must exceed Next 50 returns")

if __name__ == '__main__':
    unittest.main()
