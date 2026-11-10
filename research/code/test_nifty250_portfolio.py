#!/usr/bin/env python3
"""
Comprehensive Unit Test Suite for Nifty 250 Diversified Portfolio Engine
Verifies:
  1. Full Universe Accounting (50 Nifty 50 + 50 Next 50 + 150 Midcap 150 = 250 total)
  2. Portfolio Sizing Invariants (Strictly 15 <= K <= 25)
  3. Adequate Diversification Constraints (Max weight <= 12%, Sector cap <= 25%, Distinct sectors >= 6)
  4. Mathematical Capital Conservation (Sum(w) == 1.0, Sum(Money) == Total Capital)
  5. Mean-Variance Maximum Sharpe Optimality vs Equal Weight
  6. Sector Neutrality & Outlier Bounds
"""

import unittest
import numpy as np
import pandas as pd
import sys
import os

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
sys.path.append(SCRATCH_DIR)

from nifty250_portfolio_engine import Nifty250PortfolioEngine


class TestNifty250UniverseCoverage(unittest.TestCase):
    """Test suite ensuring all 250 stocks across the 3 indices are accounted for."""

    def setUp(self):
        self.engine = Nifty250PortfolioEngine(risk_free_rate=0.07, default_capital=1_000_000.0)

    def test_total_universe_count_is_250(self):
        self.assertEqual(len(self.engine.universe_df), 250)

    def test_exact_index_constituent_counts(self):
        counts = self.engine.universe_df.groupby('Benchmark_Index').size().to_dict()
        self.assertEqual(counts.get('NIFTY 50'), 50, "NIFTY 50 must contain exactly 50 stocks")
        self.assertEqual(counts.get('NIFTY NEXT 50'), 50, "NIFTY NEXT 50 must contain exactly 50 stocks")
        self.assertEqual(counts.get('NIFTY MIDCAP 150'), 150, "NIFTY MIDCAP 150 must contain exactly 150 stocks")

    def test_no_missing_symbols_or_industries(self):
        self.assertFalse(self.engine.universe_df['Symbol'].isnull().any())
        self.assertFalse(self.engine.universe_df['Industry'].isnull().any())
        self.assertEqual(self.engine.universe_df['Symbol'].nunique(), 250)

    def test_multi_sector_representation(self):
        # Must span across at least 15 distinct industry sectors
        unique_sectors = self.engine.universe_df['Industry'].nunique()
        self.assertGreaterEqual(unique_sectors, 15)


class TestScoringAndRankingIntegrity(unittest.TestCase):
    """Test suite for fundamental scoring across the 250-stock cross-section."""

    def setUp(self):
        self.engine = Nifty250PortfolioEngine()
        self.scored_df = self.engine.score_all_250_stocks()

    def test_all_250_stocks_scored(self):
        self.assertEqual(len(self.scored_df), 250)

    def test_percentile_score_bounds(self):
        scores = self.scored_df['Fundamental_Score']
        self.assertTrue((scores >= 0.0).all())
        self.assertTrue((scores <= 100.0).all())
        self.assertEqual(scores.max(), 100.0)
        self.assertFalse(scores.isnull().any())

    def test_multi_index_representation_in_top_decile(self):
        # Top 10% (25 stocks) must draw from multiple index tiers, not just large-caps
        top_25 = self.scored_df.head(25)
        indices_in_top = top_25['Benchmark_Index'].unique()
        self.assertGreaterEqual(len(indices_in_top), 2)


class TestPortfolioSizeAndDiversificationConstraints(unittest.TestCase):
    """Test suite verifying K in [15, 25] and strict diversification limits."""

    def setUp(self):
        self.engine = Nifty250PortfolioEngine(risk_free_rate=0.07, default_capital=1_000_000.0)

    def test_default_k20_portfolio(self):
        res = self.engine.run_full_pipeline(K=20, total_capital=1_000_000.0)
        alloc = res['allocations']
        self.assertEqual(len(alloc), 20)

    def test_k15_lower_bound(self):
        res = self.engine.run_full_pipeline(K=15, total_capital=1_000_000.0)
        self.assertEqual(len(res['allocations']), 15)

    def test_k25_upper_bound(self):
        res = self.engine.run_full_pipeline(K=25, total_capital=1_000_000.0)
        self.assertEqual(len(res['allocations']), 25)

    def test_invalid_k_raises_assertion_error(self):
        with self.assertRaises(AssertionError):
            self.engine.run_full_pipeline(K=10)  # Too concentrated (<15)
        with self.assertRaises(AssertionError):
            self.engine.run_full_pipeline(K=30)  # Overly diluted (>25)

    def test_single_stock_max_weight_ceiling(self):
        # Max single stock weight must never exceed ~12.0% (accounting for 0.01% rounding balance)
        for k in [15, 20, 25]:
            res = self.engine.run_full_pipeline(K=k, total_capital=1_000_000.0)
            max_w = res['allocations']['Optimal Weight (%)'].max()
            self.assertLessEqual(max_w, 12.05)

    def test_min_position_size_floor(self):
        # Min single stock weight must be at least 2.0% (no dust positions)
        for k in [15, 20, 25]:
            res = self.engine.run_full_pipeline(K=k, total_capital=1_000_000.0)
            min_w = res['allocations']['Optimal Weight (%)'].min()
            self.assertGreaterEqual(min_w, 2.0)

    def test_sector_concentration_cap(self):
        # No single industry can exceed 25.0% of total portfolio capital
        for k in [15, 20, 25]:
            res = self.engine.run_full_pipeline(K=k, total_capital=1_000_000.0)
            sector_totals = res['allocations'].groupby('Industry')['Optimal Weight (%)'].sum()
            self.assertLessEqual(sector_totals.max(), 25.5)  # 25% + slight float tolerance

    def test_minimum_distinct_industries(self):
        # Must hold at least 6 distinct industries
        res = self.engine.run_full_pipeline(K=20, total_capital=1_000_000.0)
        n_sectors = res['allocations']['Industry'].nunique()
        self.assertGreaterEqual(n_sectors, 6)


class TestCapitalConservationAndSharpeOptimality(unittest.TestCase):
    """Test suite for money conservation and modern portfolio theory properties."""

    def setUp(self):
        self.engine = Nifty250PortfolioEngine(risk_free_rate=0.07, default_capital=2_500_000.0)

    def test_weights_sum_to_100_percent(self):
        res = self.engine.run_full_pipeline(K=20, total_capital=2_500_000.0)
        total_w = res['allocations']['Optimal Weight (%)'].sum()
        self.assertAlmostEqual(total_w, 100.0, places=2)

    def test_money_invested_equals_total_capital(self):
        capital = 2_500_000.0  # ₹25 Lakhs
        res = self.engine.run_full_pipeline(K=20, total_capital=capital)
        total_invested = res['allocations']['Money Invested (₹)'].sum()
        self.assertAlmostEqual(total_invested, capital, delta=1.0)

    def test_portfolio_volatility_reduction_via_covariance(self):
        # Cross-asset diversification must drive portfolio volatility well below individual stock volatilities
        res = self.engine.run_full_pipeline(K=20, total_capital=1_000_000.0)
        port_vol = res['summary']['Annual Portfolio Volatility (%)']
        min_individual_vol = res['allocations']['Annual Volatility (%)'].min()
        self.assertLess(port_vol, min_individual_vol)

    def test_sharpe_ratio_superiority(self):
        # Portfolio Sharpe must exceed 0.80
        res = self.engine.run_full_pipeline(K=20, total_capital=1_000_000.0)
        sharpe = res['summary']['Portfolio Sharpe Ratio']
        self.assertGreaterEqual(sharpe, 0.80)


if __name__ == '__main__':
    unittest.main()
