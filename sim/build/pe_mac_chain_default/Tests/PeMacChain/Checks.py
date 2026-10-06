"""
Tests/PeMacChain/Checks.py
Output verification for pe_input_mux → mac_q16 chain.
Final output is from mac_q16: out_res and out_vld.
"""

from Engine.TestScenario import CheckConfig

FULL = CheckConfig(
    name    = "pe_mac_chain_full",
    signals = ["out_res"],
    filter  = "all",
)

VALID_ONLY = CheckConfig(
    name    = "pe_mac_chain_valid_only",
    signals = ["out_res"],
    filter  = "valid_only",
)
