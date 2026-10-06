"""
Tests/MacQ16/Build.py
Test plan for mac_q16. Pure data — no execution logic.

Defines which scenarios to run for this module.
run.py reads TEST_PLAN and executes each scenario.
Add more TestScenario entries to run additional combinations.
"""

from pathlib import Path

from Engine.TestScenario import TestScenario
from Engine.RTLParams import read_rtl_params
from Components.MacNode import MAC_INPUT_SPEC, MAC_OUTPUT_SPEC, mac_q16_golden_cycle
from Tests.MacQ16.Wiring import nodes, edges
from Tests.MacQ16.Stimulus import DEFAULT
from Tests.MacQ16.Checks import FULL

TEST_PLAN = [
    TestScenario(
        name        = "mac_q16_default",
        nodes       = nodes,
        edges       = edges,
        stimulus    = DEFAULT,
        checks      = FULL,
        hdl_top     = "tb_mac_q16",
        rtl_sources = ["mac_q16.sv"],
    ),
]
