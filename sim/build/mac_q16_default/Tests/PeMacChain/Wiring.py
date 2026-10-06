"""
Tests/PeMacChain/Wiring.py
Topology for pe_input_mux → mac_q16 chain. Pure data.

Signal mapping at the connection:
  mux.a_out   → mac.in_a
  mux.b_out   → mac.in_b
  mux.out_vld → mac.in_vld

Both nodes share the same DUT handle — pe_mac_wrapper exposes
all signals at the top level.
"""

from Engine.ArchBase import NodeDef
from Engine.RTLParams import read_rtl_params
from Components.MacNode import MAC_INPUT_SPEC, MAC_OUTPUT_SPEC, mac_q16_golden_cycle
from Components.MuxNode import MUX_INPUT_SPEC, MUX_OUTPUT_SPEC, pe_input_mux_golden_cycle
from Paths import TB_DIR

_mux_p = read_rtl_params(TB_DIR / "tb_pe_input_mux.sv")
_mac_p = read_rtl_params(TB_DIR / "tb_mac_q16.sv")

nodes = [
    NodeDef(
        name           = "mux",
        input_signals  = MUX_INPUT_SPEC,
        output_signals = MUX_OUTPUT_SPEC,
        golden         = pe_input_mux_golden_cycle,
        pipeline_depth = _mux_p["PIPELINE_STAGES"],
    ),
    NodeDef(
        name           = "mac",
        input_signals  = MAC_INPUT_SPEC,
        output_signals = MAC_OUTPUT_SPEC,
        golden         = mac_q16_golden_cycle,
        pipeline_depth = _mac_p["PIPELINE_STAGES"],
    ),
]
dut_keys = ["mux", "mac"]
edges = [
    ("generator", "mux"),
    ("mux", "mac", {"a_out": "in_a", "b_out": "in_b", "out_vld": "in_vld"}),
    ("mac", "collector"),
]
