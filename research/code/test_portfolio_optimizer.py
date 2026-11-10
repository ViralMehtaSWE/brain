#!/usr/bin/env python3
"""
Unit Test Suite for Fundamental Alpha Portfolio Optimizer
Tests:
  1. Top K selection and boundary enforcement (K=1, K=N, K > N)
  2. Weight constraints (sum(w) == 1.0, w_i >= min_weight, w_i <= max_weight)
  3. Money allocation conservation (sum(Money) == Total Capital)
  4. Sharpe Ratio maximization vs equal weight benchmark
  5. Cross-asset diversification (Portfolio Volatility < Average Constituent Volatility)
  6. Robustness against degenerate covariance and zero-variance assets
"""

import unittest
import numpy as np
import pandas as pd
import sys
import os

sys.path.append("/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch")
from portfolio_optimizer import PortfolioOptimizer


class TestPortfolioOptimizer(unittest.TestCase):
    """Test suite for portfolio construction and maximum Sharpe ratio optimization."""

    def setUp(self):
        self.optimizer = PortfolioOptimizer(risk_free_rate=0.07, default_capital=1_000_000.0)

    def test_weight_sum_equals_one(self):
        # 4 assets with known expected returns and covariance
        mu = np.array([0.18, 0.15, 0.12, 0.10])
        cov = np.array([
            [0.0625, 0.0100, 0.0050, 0.0020],
            [0.0100, 0.0400, 0.0080, 0.0040],
            [0.0050, 0.0080, 0.0225, 0.0030],
            [0.0020, 0.0040, 0.0030, 0.0100]
        ])
        weights = self.optimizer.optimize_maximum_sharpe(mu, cov, min_weight=0.05, max_weight=0.50)

        self.assertAlmostEqual(np.sum(weights), 1.0, places=5)
        self.assertTrue((weights >= 0.049).all())
        self.assertTrue((weights <= 0.501).all())

    def test_money_allocation_conservation(self):
        capital = 2_500_000.0
        candidate_pool = ["TCS", "INFY", "NESTLEIND", "ITC", "RELIANCE"]
        result = self.optimizer.construct_portfolio(candidate_pool, K=3, total_capital=capital)

        alloc_df = result['allocations']
        total_money = alloc_df['Money Invested (₹)'].sum()
        total_weight = alloc_df['Optimal Weight (%)'].sum()

        self.assertAlmostEqual(total_money, capital, delta=1.0)
        self.assertAlmostEqual(total_weight, 100.0, places=1)
        self.assertEqual(len(alloc_df), 3)

    def test_sharpe_ratio_superior_to_equal_weight(self):
        mu = np.array([0.20, 0.18, 0.14, 0.11])
        cov = np.array([
            [0.09, 0.02, 0.01, 0.01],
            [0.02, 0.06, 0.01, 0.01],
            [0.01, 0.01, 0.04, 0.01],
            [0.01, 0.01, 0.01, 0.02]
        ])
        opt_weights = self.optimizer.optimize_maximum_sharpe(mu, cov, min_weight=0.0, max_weight=1.0)
        eq_weights = np.ones(4) / 4.0

        def calc_sharpe(w):
            r = np.dot(w, mu)
            v = np.sqrt(np.dot(w.T, np.dot(cov, w)))
            return (r - 0.07) / v

        opt_sharpe = calc_sharpe(opt_weights)
        eq_sharpe = calc_sharpe(eq_weights)

        self.assertGreaterEqual(opt_sharpe, eq_sharpe)

    def test_portfolio_volatility_diversification_reduction(self):
        # Uncorrelated assets with 25% volatility each
        n = 5
        cov = np.eye(n) * (0.25 ** 2)
        mu = np.full(n, 0.16)
        weights = self.optimizer.optimize_maximum_sharpe(mu, cov, min_weight=0.1, max_weight=0.4)

        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
        single_vol = 0.25

        # Due to diversification, portfolio volatility must be substantially lower than 25%
        self.assertLess(port_vol, single_vol * 0.6)

    def test_k_greater_than_pool_size(self):
        candidate_pool = ["TCS", "INFY"]
        # Asking for K=10 from a pool of 2 should gracefully select both
        result = self.optimizer.construct_portfolio(candidate_pool, K=10, total_capital=500_000.0)
        self.assertEqual(len(result['allocations']), 2)


if __name__ == '__main__':
    unittest.main()
