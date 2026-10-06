"""
Tests/PeMacChain/Build.py
Test plan for pe_input_mux → mac_q16 chain. Pure data.
"""

from Engine.TestScenario import TestScenario
from Tests.PeMacChain.Wiring import nodes, edges
from Tests.PeMacChain.Stimulus import DEFAULT
from Tests.PeMacChain.Checks import FULL

TEST_PLAN = [
    TestScenario(
        name        = "pe_mac_chain_default",
        nodes       = nodes,
        edges       = edges,
        stimulus    = DEFAULT,
        checks      = FULL,
        hdl_top     = "tb_pe_mac_wrapper",
        rtl_sources = ["pe_input_mux.sv", "mac_q16.sv", "pe_mac_wrapper.sv"],
    ),
]
