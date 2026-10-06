"""
Tests/MacQ16/Checks.py
Output verification definitions for mac_q16.
One CheckConfig = one complete check scenario.
Add more named configs below for additional check variants.
"""

from Engine.TestScenario import CheckConfig

# ── Full check — compare every cycle ─────────────────────────────
FULL = CheckConfig(
    name    = "mac_q16_full",
    signals = ["out_res"],
    filter  = "all",
)

# ── Valid only — compare only cycles where out_vld=1 ─────────────
VALID_ONLY = CheckConfig(
    name    = "mac_q16_valid_only",
    signals = ["out_res"],
    filter  = "valid_only",
)
