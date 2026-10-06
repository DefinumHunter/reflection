"""
Tests/PeInputMux/Checks.py
Output verification definitions for pe_input_mux.
"""

from Engine.TestScenario import CheckConfig

FULL = CheckConfig(
    name    = "pe_input_mux_full",
    signals = ["a_out", "b_out"],
    filter  = "all",
)

VALID_ONLY = CheckConfig(
    name    = "pe_input_mux_valid_only",
    signals = ["a_out", "b_out"],
    filter  = "valid_only",
)
