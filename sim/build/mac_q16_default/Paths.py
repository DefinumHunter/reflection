"""
sim/Paths.py
Single source of truth for all filesystem paths.

Searches upward from this file's location for the repo root,
identified by the presence of run.py. Works correctly even when
this file is copied into sim/build/mac_q16/ by the test runner.
"""

from pathlib import Path


def _find_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "run.py").exists():
            return p
        p = p.parent
    raise RuntimeError("Could not find repo root (run.py not found in any parent directory)")


ROOT        = _find_root()
SIM_DIR     = ROOT    / "sim"
RTL_DIR     = ROOT    / "rtl"
TB_DIR      = ROOT    / "tb"
RESULTS_DIR = SIM_DIR / "Results"
BUILD_DIR   = SIM_DIR / "build"
TESTS_DIR   = SIM_DIR / "Tests"