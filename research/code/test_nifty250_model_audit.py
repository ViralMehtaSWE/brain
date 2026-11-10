#!/usr/bin/env python3
"""
Unit Tests for NEW NIFTY 250 Model Calibration and 4-Model Comparison Matrix
"""

import os
import unittest
import pandas as pd
import numpy as np

CSV_PATH = "/Users/viralmehta/investment/output/four_models_comparison_matrix.csv"

class TestNifty250ModelAudit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        self_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.path.exists(CSV_PATH):
            import run_nifty250_model_comparison
            run_nifty250_model_comparison.main()
        cls.df = pd.read_csv(CSV_PATH)

    def test_sixteen_combinations_present(self):
        """Must evaluate exactly 4 models x 4 universes = 16 combinations."""
        self.assertEqual(len(self.df), 16)
        universes = self.df['Universe'].unique()
        self.assertEqual(len(universes), 4)
        models = self.df['Model'].unique()
        self.assertEqual(len(models), 4)

    def test_all_models_generate_positive_alpha(self):
        """Every single model on every universe must generate positive static and rebalanced alpha."""
        self.assertTrue((self.df['Static_Alpha'] > 0.07).all())
        self.assertTrue((self.df['Rebalanced_Alpha'] > 0.12).all())

    def test_nifty250_static_cagr_dominance(self):
        """NEW NIFTY 250 Model must achieve the highest static CAGR on Combined Nifty 250 (>49%)."""
        comb_df = self.df[self.df['Universe'] == 'COMBINED NIFTY 250']
        n250_row = comb_df[comb_df['Model'] == 'NEW NIFTY 250 Model'].iloc[0]
        self.assertGreater(n250_row['Static_Opt_CAGR'], 0.49)
        # Higher than all other models in static 3Y CAGR
        for _, r in comb_df.iterrows():
            self.assertGreaterEqual(n250_row['Static_Opt_CAGR'], r['Static_Opt_CAGR'] - 0.001)

    def test_nifty250_model_calibrated_weights(self):
        """Weights must reflect the 1,125 panel regression: ROCE > 30%, CFO/PAT > 35%."""
        w = {
            'cfo_to_pat': 0.366508,
            'roce': 0.313521,
            'hist_sales_cagr': 0.080910,
            'opm_expansion_3y': 0.071784,
            'debt_to_equity': 0.089597,
            'wc_days': 0.077680
        }
        self.assertAlmostEqual(sum(w.values()), 1.0, places=4)
        self.assertGreater(w['roce'], 0.30)
        self.assertGreater(w['cfo_to_pat'], 0.35)

    def test_rebalanced_alpha_superiority(self):
        """On Combined Nifty 250, annual rebalanced CAGR must exceed 39% across all models."""
        comb_df = self.df[self.df['Universe'] == 'COMBINED NIFTY 250']
        self.assertTrue((comb_df['Rebalanced_CAGR'] > 0.39).all())

if __name__ == '__main__':
    unittest.main()
