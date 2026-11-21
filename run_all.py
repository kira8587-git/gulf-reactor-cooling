"""Run the tests, then all experiments (about a minute, no internet needed).

    python run_all.py
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    if pytest.main(["-q", str(ROOT / "tests")]) != 0:
        sys.exit("Tests failed: fix them before trusting any result.")
    import experiments
    sys.exit(experiments.main([]))
