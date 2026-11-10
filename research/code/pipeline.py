#!/usr/bin/env python3
"""
Master Pipeline: Executes Extraction, Predictive Power Analysis, 
and Generates the Structured Artifact Report.
"""
import subprocess
import sys
import os

SCRATCH_DIR = "/Users/viralmehta/.gemini/antigravity-cli/brain/7d4b83c2-c66a-4f9e-8a3b-9192a3ba2d22/scratch"
PYTHON_BIN = "/Users/viralmehta/investment/venv/bin/python3"

def run_step(cmd_list, desc):
    print(f"\n>>> Running: {desc}...")
    res = subprocess.run(cmd_list, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error in {desc}:\n{res.stderr}")
        sys.exit(1)
    print(res.stdout)

if __name__ == '__main__':
    # Step 1: Parse and extract features & targets
    run_step([PYTHON_BIN, os.path.join(SCRATCH_DIR, "parse_and_extract.py")], "Feature & Target Extraction")

    # Step 2: Run quantitative factor research & stock scoring
    run_step([PYTHON_BIN, os.path.join(SCRATCH_DIR, "run_predictive_analysis.py")], "Predictive Power Analysis & Stock Scoring")
