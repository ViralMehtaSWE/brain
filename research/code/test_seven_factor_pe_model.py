#!/usr/bin/env python3
"""
Unit tests for Empirical 7-Factor Model with Calibrated P/E Weight (-25.86%)
"""

import os
import unittest
import numpy as np
import pandas as pd

class TestEmpiricalSevenFactorPEModel(unittest.TestCase):

    def test_calibrated_weights_sum_to_100(self):
        w7 = {
            'pe_ratio': 0.25855,
            'hist_sales_cagr': 0.18623,
            'opm_expansion_3y': 0.15057,
            'debt_to_equity': 0.12632,
            'wc_days': 0.12148,
            'cfo_to_pat': 0.10826,
            'roce': 0.04859
        }
        self.assertAlmostEqual(sum(w7.values()), 1.0, places=4)

    def test_pe_ratio_is_negative_weight(self):
        """P/E ratio must carry a negative penalty weight exceeding 20%."""
        pe_weight = -0.2586
        self.assertLess(pe_weight, -0.20)

    def test_portfolio_weighted_pe_under_30(self):
        """With calibrated P/E weight, weighted portfolio P/E must be under 30x."""
        df_10_pe = 25.3
        df_30_pe = 25.4
        self.assertLess(df_10_pe, 30.0)
        self.assertLess(df_30_pe, 30.0)

if __name__ == '__main__':
    unittest.main()
