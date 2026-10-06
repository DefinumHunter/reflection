"""
Tests/PeInputMux/Build.py
Test plan for pe_input_mux. Pure data — no execution logic.
"""

from Engine.TestScenario import TestScenario
from Tests.PeInputMux.Wiring import nodes, edges
from Tests.PeInputMux.Stimulus import DEFAULT
from Tests.PeInputMux.Checks import FULL

TEST_PLAN = [
    TestScenario(
        name        = "pe_input_mux_default",
        nodes       = nodes,
        edges       = edges,
        stimulus    = DEFAULT,
        checks      = FULL,
        hdl_top     = "tb_pe_input_mux",
        rtl_sources = ["pe_input_mux.sv"],
    ),
]
