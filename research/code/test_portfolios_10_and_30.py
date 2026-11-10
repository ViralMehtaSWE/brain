#!/usr/bin/env python3
"""
Unit tests for 10-stock and 30-stock portfolio generations
"""

import os
import unittest
import pandas as pd
import numpy as np

CSV_10 = "/Users/viralmehta/investment/output/nifty250_top10_stocks.csv"
CSV_30 = "/Users/viralmehta/investment/output/nifty250_top30_stocks.csv"

class TestPortfolios(unittest.TestCase):

    def test_ten_stock_portfolio(self):
        df = pd.read_csv(CSV_10)
        self.assertEqual(len(df), 10)
        self.assertAlmostEqual(df['optimal_weight_pct'].sum(), 100.0, places=1)
        self.assertAlmostEqual(df['invest_10L_opt'].sum(), 1_000_000.0, delta=100.0)
        self.assertAlmostEqual(df['invest_1CR_opt'].sum(), 10_000_000.0, delta=1000.0)
        # Check high ROCE
        w = df['optimal_weight_pct'] / 100.0
        weighted_roce = np.dot(w, df['roce'])
        self.assertGreater(weighted_roce, 60.0)

    def test_thirty_stock_portfolio(self):
        df = pd.read_csv(CSV_30)
        self.assertEqual(len(df), 30)
        self.assertAlmostEqual(df['optimal_weight_pct'].sum(), 100.0, places=1)
        self.assertAlmostEqual(df['invest_10L_opt'].sum(), 1_000_000.0, delta=100.0)
        self.assertAlmostEqual(df['invest_1CR_opt'].sum(), 10_000_000.0, delta=1000.0)
        self.assertGreaterEqual(df['industry'].nunique(), 10)

if __name__ == '__main__':
    unittest.main()
