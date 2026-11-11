---
title: Mandatory Quantitative Alpha & Valuation Rules
type: note
permalink: obsidian/mandatory-quantitative-alpha-valuation-rules
---

# Mandatory Quantitative Alpha & Valuation Rules

## Core Directives for Portfolio Construction & Stock Selection

### 1. Always Incorporate Valuation (P/E Ratio)
- **Zero Valuation-Blindness:** Never select, rank, or recommend stocks purely on business quality or historical earnings growth without evaluating the price paid.
- **Valuation Penalty Weight:** Multi-factor portfolio scoring must explicitly penalize elevated multiples using a negative sector-neutral P/E weight ($-w_{\text{PE}} \cdot Z_{\text{Sector}}(\text{P/E})$).
- **Valuation Safety Gate:** Hard exclusion or strict gating for bubble multiples ($\text{P/E} > 80\text{x}$) to protect against catastrophic multiple de-rating.

### 2. Strict Zero-Fabrication Mandate (Real Empirical Data Only)
- **Authentic Sources Only:** All equity fundamentals, quarterly earnings, annual statements, shareholding patterns, and historical price series must originate from authentic exchange data (NSE closing series) and audited regulatory filings (via Screener.in / NSE).
- **Zero Hallucination / Synthetic Data:** Never invent, extrapolate, synthesize, or fallback to mock numbers (such as arbitrary CAGRs or synthetic covariance). If data is missing or track records are insufficient ($< 365$ days), the system must explicitly fail or gate the asset.

### 3. Institutional Portfolio Constraints
- **Stock Box Bounds:** Maximum single-stock allocation capped at $\le 8.0\%$ to enforce idiosyncratic diversification; minimum position $\ge 2.5\%$ to prevent dust holdings.
- **Sector Exposure Cap:** Maximum capital allocated to any single industry sector strictly capped at $\le 25.0\%$.
- **Sector Breadth:** Portfolio must span at least 7 distinct industry sectors with no more than 3 stocks per sector.
