"""
Tests/PeInputMux/Wiring.py
Topology for pe_input_mux standalone test. Pure data — no execution logic.
"""

from Engine.ArchBase import NodeDef
from Engine.RTLParams import read_rtl_params
from Components.MuxNode import MUX_INPUT_SPEC, MUX_OUTPUT_SPEC, pe_input_mux_golden_cycle
from Paths import TB_DIR

_p = read_rtl_params(TB_DIR / "tb_pe_input_mux.sv")

nodes = [
    NodeDef(
        name           = "mux",
        input_signals  = MUX_INPUT_SPEC,
        output_signals = MUX_OUTPUT_SPEC,
        golden         = pe_input_mux_golden_cycle,
        pipeline_depth = _p["PIPELINE_STAGES"],
    ),
]
dut_keys = ["mux"]
edges = [
    ("generator", "mux"),
    ("mux",       "collector"),
]