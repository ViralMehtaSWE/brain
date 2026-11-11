import os
import sys

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
RESEARCH_DIR = os.path.abspath(os.path.join(CODE_DIR, ".."))
DATA_DIR = os.path.join(RESEARCH_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, "screener_cache")
PRICES_DIR = os.path.join(DATA_DIR, "prices")
PRICE_10Y_DIR = os.path.join(DATA_DIR, "price_10y")
UNIVERSE_CSV = os.path.join(DATA_DIR, "nifty_250_universe.csv")
CALIBRATION_JSON = os.path.join(DATA_DIR, "audited_three_universes_calibration.json")
OUTPUT_DIR = os.path.join(RESEARCH_DIR, "output")

# Fallback scratch directory for backward compatibility if needed
LEGACY_SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
SCRATCH_DIR = DATA_DIR if os.path.exists(DATA_DIR) else LEGACY_SCRATCH_DIR

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
