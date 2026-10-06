"""
Tests/MacQ16/Wiring.py
Topology for mac_q16 standalone test. Pure data — no execution logic.

Exports nodes and edges. Callers decide what to build:
  - run.py stage 1: build_reference(nodes, edges)
  - Simulate.py stage 4: build_simulation(nodes, edges, duts)
"""

from Engine.ArchBase import NodeDef
from Engine.RTLParams import read_rtl_params
from Components.MacNode import MAC_INPUT_SPEC, MAC_OUTPUT_SPEC, mac_q16_golden_cycle
from Paths import TB_DIR

_p = read_rtl_params(TB_DIR / "tb_mac_q16.sv")

nodes = [
    NodeDef(
        name           = "mac",
        input_signals  = MAC_INPUT_SPEC,
        output_signals = MAC_OUTPUT_SPEC,
        golden         = mac_q16_golden_cycle,
        pipeline_depth = _p["PIPELINE_STAGES"],
    ),
]
dut_keys = ["mac"]
edges = [
    ("generator", "mac"),
    ("mac",       "collector"),
]