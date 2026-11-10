#!/usr/bin/env python3
"""
Unit tests for Regenerated 3x3 Cross-Universe Matrix with P/E Feature
"""

import os
import unittest
import pandas as pd
import numpy as np

CSV_PATH = "/Users/viralmehta/investment/output/regenerated_3x3_matrix_with_pe.csv"

class TestRegenerated3x3MatrixWithPE(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(CSV_PATH):
            import run_seven_factor_cross_matrix
            run_seven_factor_cross_matrix.main()
        cls.df = pd.read_csv(CSV_PATH)

    def test_nine_combinations_present(self):
        """Must contain exactly 3 models x 3 universes = 9 rows."""
        self.assertEqual(len(self.df), 9)
        self.assertEqual(len(self.df['Universe'].unique()), 3)
        self.assertEqual(len(self.df['Model'].unique()), 3)

    def test_all_alphas_positive(self):
        """Every single cell must produce positive static and rebalanced alpha."""
        self.assertTrue((self.df['Static_Alpha'] > 0.07).all())
        self.assertTrue((self.df['Rebalanced_Alpha'] > 0.15).all())

    def test_midcap_model_strict_pe(self):
        """Midcap 150 Model must hold average P/E under 30x across all universes."""
        sub = self.df[self.df['Model'] == 'NIFTY MIDCAP 150 Model (7F)']
        self.assertTrue((sub['Average_PE'] < 30.0).all())

    def test_next50_rebalanced_dominance_on_home(self):
        """Next 50 Model must win annual rebalanced CAGR on Nifty Next 50 (>34%)."""
        next50_sub = self.df[self.df['Universe'] == 'NIFTY NEXT 50']
        winner = next50_sub.sort_values('Rebalanced_CAGR', ascending=False).iloc[0]
        self.assertEqual(winner['Model'], 'NIFTY NEXT 50 Model (7F)')
        self.assertGreater(winner['Rebalanced_CAGR'], 0.34)

if __name__ == '__main__':
    unittest.main()
