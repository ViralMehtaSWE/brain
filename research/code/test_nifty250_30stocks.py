#!/usr/bin/env python3
"""
Unit Tests for NIFTY 250 Top 30 Stocks Portfolio Selection Engine
Using the NIFTY NEXT 50 Model
"""

import os
import unittest
import pandas as pd
import numpy as np

CSV_PATH = "/Users/viralmehta/investment/output/nifty250_30stocks_next50_model.csv"

class TestNifty250ThirtyStockPortfolio(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(CSV_PATH):
            from select_nifty250_30stocks import main
            main()
        cls.df = pd.read_csv(CSV_PATH)

    def test_exact_thirty_stocks(self):
        """Must contain exactly 30 stocks."""
        self.assertEqual(len(self.df), 30)

    def test_optimal_weights_sum_to_100(self):
        """Optimal weights must sum to 100.00%."""
        total_w = self.df['optimal_weight_pct'].sum()
        self.assertAlmostEqual(total_w, 100.0, places=1)

    def test_position_sizing_bounds(self):
        """Each stock must adhere to min 1.5% and max 6.0% bounds."""
        self.assertTrue((self.df['optimal_weight_pct'] >= 1.49).all())
        self.assertTrue((self.df['optimal_weight_pct'] <= 6.01).all())

    def test_sector_diversification(self):
        """No single industry should exceed 4 stocks."""
        counts = self.df['industry'].value_counts()
        self.assertTrue((counts <= 4).all())
        self.assertGreaterEqual(self.df['industry'].nunique(), 10)

    def test_fundamental_quality(self):
        """Weighted ROCE must exceed 35% and debt-to-equity below 0.50."""
        w = self.df['optimal_weight_pct'] / 100.0
        weighted_roce = np.dot(w, self.df['roce'])
        weighted_de = np.dot(w, self.df['debt_to_equity'])
        weighted_cfo_pat = np.dot(w, self.df['cfo_to_pat'])
        self.assertGreater(weighted_roce, 35.0)
        self.assertLess(weighted_de, 0.50)
        self.assertGreater(weighted_cfo_pat, 1.00)

    def test_investment_amounts_match_capital(self):
        """Investment amounts must correctly add up to ₹10 Lakhs and ₹1 Crore."""
        self.assertAlmostEqual(self.df['invest_10L_opt'].sum(), 1_000_000.0, delta=100.0)
        self.assertAlmostEqual(self.df['invest_1CR_opt'].sum(), 10_000_000.0, delta=1000.0)

if __name__ == '__main__':
    unittest.main()
