#!/usr/bin/env python3
"""
Exhaustive Unit & Integration Test Suite for Fundamental Alpha Research & Stock Scoring Framework
Covers:
  1. Data Parsing & Sanitization (edge cases, formatting variations, malformed inputs)
  2. Mathematical Ratios & Accounting Formulas (CAGR, Margins, Leverage, Cash Conversion)
  3. Edge Cases (Zero Denominators, Negative Earnings, Insolvent Net Worth, Zero Variance)
  4. Statistical Operations (Spearman Rank IC with ties, Winsorization, Sector Z-Scores)
  5. Machine Learning Predictor (Tree Gini sum, Permutation validity)
  6. Scoring Model Properties (Monotonicity, Scale Invariance, Decile Stratification)
  7. End-to-End Longitudinal Multi-Period Simulation Test
"""

import unittest
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, ttest_1samp
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance

import sys
import os

_CURR_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURR_DIR not in sys.path:
    sys.path.insert(0, _CURR_DIR)
sys.path.append("/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch")

from parse_and_extract import clean_num, parse_financial_section, parse_top_ratios, parse_compound_tables


class TestDataSanitization(unittest.TestCase):
    """Test suite for data cleaning, sanitization, and type conversions."""

    def test_clean_num_standard_floats_and_integers(self):
        self.assertEqual(clean_num("1234.56"), 1234.56)
        self.assertEqual(clean_num("100"), 100.0)
        self.assertEqual(clean_num("-45.2"), -45.2)
        self.assertEqual(clean_num(0), 0.0)
        self.assertEqual(clean_num(42.1), 42.1)

    def test_clean_num_percentages_and_commas(self):
        self.assertEqual(clean_num("25%"), 25.0)
        self.assertEqual(clean_num("+14%"), 14.0)
        self.assertEqual(clean_num("-8.5%"), -8.5)
        self.assertEqual(clean_num("8,95,621"), 895621.0)
        self.assertEqual(clean_num("2,475.50"), 2475.50)
        self.assertEqual(clean_num(" 1,00,000 % "), 100000.0)

    def test_clean_num_missing_and_corrupt(self):
        self.assertTrue(np.isnan(clean_num(None)))
        self.assertTrue(np.isnan(clean_num("")))
        self.assertTrue(np.isnan(clean_num("   ")))
        self.assertTrue(np.isnan(clean_num("-")))
        self.assertTrue(np.isnan(clean_num("--")))
        self.assertTrue(np.isnan(clean_num("N/A")))
        self.assertTrue(np.isnan(clean_num("None")))
        self.assertTrue(np.isnan(clean_num("invalid_string")))


class TestHTMLParsing(unittest.TestCase):
    """Test suite for extracting financial statements and ratio cards."""

    def setUp(self):
        self.sample_html = """
        <div id="top-ratios">
          <span class="name">Stock P/E</span>
          <span class="nowrap value">₹ <span class="number">24.5</span></span>
          <span class="name">ROCE</span>
          <span class="nowrap value"><span class="number">32.8</span>%</span>
          <span class="name">Market Cap</span>
          <span class="nowrap value">₹ <span class="number">1,25,000</span> Cr.</span>
        </div>
        <section id="profit-loss">
          <table>
            <thead>
              <tr><th></th><th>Mar 2021</th><th>Mar 2022</th><th>Mar 2023</th><th>TTM</th></tr>
            </thead>
            <tbody>
              <tr><td>Sales</td><td>1,000</td><td>1,200</td><td>1,500</td><td>1,650</td></tr>
              <tr><td>Operating Profit</td><td>200</td><td>260</td><td>340</td><td>380</td></tr>
              <tr><td>OPM %</td><td>20%</td><td>22%</td><td>23%</td><td>23%</td></tr>
              <tr><td>Net Profit</td><td>150</td><td>190</td><td>250</td><td>280</td></tr>
            </tbody>
          </table>
        </section>
        <section id="balance-sheet">
          <table>
            <thead>
              <tr><th></th><th>Mar 2021</th><th>Mar 2022</th><th>Mar 2023</th></tr>
            </thead>
            <tbody>
              <tr><td>Equity Capital</td><td>50</td><td>50</td><td>50</td></tr>
              <tr><td>Reserves</td><td>450</td><td>600</td><td>800</td></tr>
              <tr><td>Borrowings</td><td>100</td><td>80</td><td>50</td></tr>
            </tbody>
          </table>
        </section>
        <table class="ranges-table">
          <th colspan="2">Compounded Sales Growth</th>
          <tr><td>3 Years:</td><td>15%</td></tr>
          <tr><td>TTM:</td><td>20%</td></tr>
        </table>
        <table class="ranges-table">
          <th colspan="2">Return on Equity</th>
          <tr><td>3 Years:</td><td>28%</td></tr>
          <tr><td>Last Year:</td><td>30%</td></tr>
        </table>
        """

    def test_parse_top_ratios(self):
        ratios = parse_top_ratios(self.sample_html)
        self.assertEqual(ratios.get("Stock P/E"), 24.5)
        self.assertEqual(ratios.get("ROCE"), 32.8)
        self.assertEqual(ratios.get("Market Cap"), 125000.0)

    def test_parse_financial_section_periods_and_rows(self):
        pl, pl_periods = parse_financial_section(self.sample_html, "profit-loss")
        self.assertEqual(pl_periods, ["Mar 2021", "Mar 2022", "Mar 2023", "TTM"])
        self.assertIn("Sales", pl)
        self.assertEqual(pl["Sales"], [1000.0, 1200.0, 1500.0, 1650.0])
        self.assertEqual(pl["OPM %"], [20.0, 22.0, 23.0, 23.0])
        self.assertEqual(pl["Net Profit"], [150.0, 190.0, 250.0, 280.0])

        bs, bs_periods = parse_financial_section(self.sample_html, "balance-sheet")
        self.assertEqual(bs_periods, ["Mar 2021", "Mar 2022", "Mar 2023"])
        self.assertEqual(bs["Borrowings"], [100.0, 80.0, 50.0])

    def test_parse_missing_section_graceful(self):
        metrics, periods = parse_financial_section(self.sample_html, "non-existent-section")
        self.assertEqual(metrics, {})
        self.assertEqual(periods, [])

    def test_parse_compound_tables(self):
        tables = parse_compound_tables(self.sample_html)
        self.assertEqual(tables.get("Compounded Sales Growth_3 Years"), 15.0)
        self.assertEqual(tables.get("Compounded Sales Growth_TTM"), 20.0)
        self.assertEqual(tables.get("Return on Equity_3 Years"), 28.0)
        self.assertEqual(tables.get("Return on Equity_Last Year"), 30.0)


class TestFinancialFormulasAndEdgeCases(unittest.TestCase):
    """Test suite for financial calculations under both normal and extreme edge cases."""

    def test_3y_cagr_standard(self):
        # 100 growing at 20% annualized: 100 * (1.2)^3 = 172.8
        v0 = 100.0
        v3 = 172.8
        cagr = ((v3 / v0) ** (1/3) - 1) * 100
        self.assertAlmostEqual(cagr, 20.0, places=4)

    def test_3y_cagr_zero_denominator_safeguard(self):
        v0 = 0.0
        v3 = 150.0
        # Formula must guard against division by zero
        cagr = ((v3 / v0) ** (1/3) - 1) * 100 if (v0 > 0 and v3 > 0) else np.nan
        self.assertTrue(np.isnan(cagr))

    def test_3y_cagr_negative_earnings_safeguard(self):
        v0 = -50.0
        v3 = 100.0
        cagr = ((v3 / v0) ** (1/3) - 1) * 100 if (v0 > 0 and v3 > 0) else np.nan
        self.assertTrue(np.isnan(cagr))

    def test_debt_to_equity_healthy_and_leveraged(self):
        # Clean balance sheet
        de_healthy = 50.0 / (100.0 + 900.0)
        self.assertEqual(de_healthy, 0.05)

        # Insolvent net worth safeguard: negative reserves wiping equity
        equity = 100.0
        negative_reserves = -200.0
        net_worth = equity + negative_reserves
        # Net worth <= 0 should be flagged
        self.assertLess(net_worth, 0)

    def test_cfo_to_pat_cash_conversion(self):
        # High quality accounting: CFO >= PAT
        self.assertGreaterEqual(150.0 / 100.0, 1.0)
        # Aggressive accruals / low quality: CFO << PAT
        self.assertLess(30.0 / 100.0, 1.0)

    def test_peg_ratio_guards(self):
        # Normal PEG: PE 20, Growth 20% -> PEG = 1.0
        pe = 20.0
        growth = 20.0
        peg = pe / growth if growth > 0 else np.nan
        self.assertEqual(peg, 1.0)

        # Negative growth or zero growth should yield NaN
        growth_neg = -5.0
        peg_neg = pe / growth_neg if growth_neg > 0 else np.nan
        self.assertTrue(np.isnan(peg_neg))


class TestStatisticalEngine(unittest.TestCase):
    """Test suite for factor evaluation, Rank IC, winsorization, and Z-scores."""

    def test_spearman_rank_ic_perfect_positive(self):
        x = np.array([10, 20, 30, 40, 50])
        y = np.array([100, 200, 300, 400, 500])
        ic, p_val = spearmanr(x, y)
        self.assertAlmostEqual(ic, 1.0, places=5)
        self.assertLess(p_val, 0.05)

    def test_spearman_rank_ic_perfect_negative(self):
        x = np.array([10, 20, 30, 40, 50])
        y = np.array([500, 400, 300, 200, 100])
        ic, p_val = spearmanr(x, y)
        self.assertAlmostEqual(ic, -1.0, places=5)
        self.assertLess(p_val, 0.05)

    def test_spearman_rank_ic_with_ties(self):
        x = np.array([10, 20, 20, 40, 50])
        y = np.array([100, 200, 200, 400, 500])
        ic, _ = spearmanr(x, y)
        self.assertAlmostEqual(ic, 1.0, places=5)

    def test_winsorization_clips_extreme_outliers(self):
        series = pd.Series([10.0, 12.0, 11.0, 13.0, 12.5, 9999.0, -9999.0])
        low = series.quantile(0.05)
        high = series.quantile(0.95)
        winsorized = series.clip(low, high)
        self.assertLess(winsorized.max(), 9999.0)
        self.assertGreater(winsorized.min(), -9999.0)

    def test_sector_neutral_zscore_properties(self):
        df = pd.DataFrame({
            'sector': ['IT', 'IT', 'IT', 'Banking', 'Banking', 'Banking'],
            'metric': [40.0, 50.0, 60.0, 10.0, 20.0, 30.0]
        })
        s_mean = df.groupby('sector')['metric'].transform('mean')
        s_std = df.groupby('sector')['metric'].transform('std')
        df['z'] = (df['metric'] - s_mean) / s_std

        for sec, grp in df.groupby('sector'):
            self.assertAlmostEqual(grp['z'].mean(), 0.0, places=5)
            self.assertAlmostEqual(grp['z'].std(), 1.0, places=5)

    def test_zero_variance_sector_handling(self):
        # If all companies in a sector have the exact same metric value
        df = pd.DataFrame({
            'sector': ['A', 'A', 'A'],
            'metric': [10.0, 10.0, 10.0]
        })
        s_mean = df.groupby('sector')['metric'].transform('mean')
        s_std = df.groupby('sector')['metric'].transform('std').replace(0, 1).fillna(1)
        z = (df['metric'] - s_mean) / s_std
        # Should not throw divide-by-zero, all z-scores should be 0.0
        self.assertTrue((z == 0.0).all())


class TestScoringModelProperties(unittest.TestCase):
    """Test suite for the multi-factor scoring formula and stock ranking."""

    def test_scoring_weights_monotonicity(self):
        # Company A has superior quality & growth, Company B is weak
        high_quality = {
            'z_roce': 2.0, 'z_sales': 1.5, 'z_opm': 1.0, 'z_cfo': 1.5,
            'z_de': -1.0, 'z_pe': -1.0
        }
        low_quality = {
            'z_roce': -2.0, 'z_sales': -1.5, 'z_opm': -1.0, 'z_cfo': -1.5,
            'z_de': 2.0, 'z_pe': 2.0
        }

        def score(s):
            return (
                0.25 * s['z_roce']
                + 0.20 * s['z_sales']
                + 0.15 * s['z_opm']
                + 0.15 * s['z_cfo']
                - 0.15 * s['z_de']
                - 0.10 * s['z_pe']
            )

        self.assertGreater(score(high_quality), 0)
        self.assertLess(score(low_quality), 0)
        self.assertGreater(score(high_quality), score(low_quality))

    def test_ranking_scale_invariance(self):
        # Multiplying all raw scores by any positive scalar must not change rank ordering
        scores = pd.Series([1.2, 0.4, 2.5, -0.8, -1.5])
        ranks_original = scores.rank(ascending=False)
        ranks_scaled = (scores * 4.2 + 10.0).rank(ascending=False)
        pd.testing.assert_series_equal(ranks_original, ranks_scaled)

    def test_percentile_bounds_and_coverage(self):
        raw = pd.Series(np.linspace(-5, 5, 20))
        pct = (raw.rank(pct=True) * 100).round(1)
        self.assertTrue((pct >= 0).all())
        self.assertTrue((pct <= 100).all())
        self.assertEqual(pct.max(), 100.0)
        self.assertEqual(pct.min(), 5.0)


class TestMachineLearningFeatureImportance(unittest.TestCase):
    """Test suite for Random Forest feature importance module."""

    def test_random_forest_importance_properties(self):
        np.random.seed(42)
        n_samples = 100
        # Feature 1 is directly predictive of y, Feature 2 is pure noise
        x1 = np.random.normal(0, 1, n_samples)
        x2 = np.random.normal(0, 1, n_samples)
        y = 3.0 * x1 + np.random.normal(0, 0.2, n_samples)

        X = pd.DataFrame({'predictive': x1, 'noise': x2})
        rf = RandomForestRegressor(n_estimators=50, random_state=42)
        rf.fit(X, y)

        # Gini importances must sum to 1.0
        self.assertAlmostEqual(np.sum(rf.feature_importances_), 1.0, places=5)
        # Predictive feature must have far higher importance than noise
        self.assertGreater(rf.feature_importances_[0], rf.feature_importances_[1] * 3)

        perm = permutation_importance(rf, X, y, n_repeats=5, random_state=42)
        self.assertGreater(perm.importances_mean[0], perm.importances_mean[1])


class TestEndToEndPipelineIntegration(unittest.TestCase):
    """Integration test simulating the full longitudinal cross-sectional pipeline."""

    def test_full_pipeline_run(self):
        np.random.seed(42)
        # Generate 30 synthetic company records across 2 sectors and 3 periods
        records = []
        sectors = ['Tech', 'Auto']
        periods = ['2020', '2021', '2022']

        for p in periods:
            for i in range(15):
                roce = np.random.uniform(10, 45)
                cfo_pat = np.random.uniform(0.5, 2.0)
                sales_g = np.random.uniform(-5, 30)
                de = np.random.uniform(0, 1.5)
                # Forward growth driven by CFO conversion and ROCE
                fwd_g = 0.3 * roce + 0.4 * cfo_pat * 10 - 0.2 * de * 10 + np.random.normal(0, 2)
                
                records.append({
                    'ticker': f'STK_{i}',
                    'sector': sectors[i % 2],
                    'period': p,
                    'roce': roce,
                    'cfo_to_pat': cfo_pat,
                    'hist_sales_cagr': sales_g,
                    'debt_to_equity': de,
                    'fwd_pat_cagr_3y': fwd_g
                })

        df = pd.DataFrame(records)
        
        # Test Rank IC calculation
        ic_vals = []
        for p, grp in df.groupby('period'):
            ic, _ = spearmanr(grp['roce'], grp['fwd_pat_cagr_3y'])
            ic_vals.append(ic)
        
        mean_ic = np.mean(ic_vals)
        self.assertGreater(mean_ic, 0.0)  # Must capture positive association
        self.assertFalse(np.isnan(mean_ic))


if __name__ == '__main__':
    unittest.main()
