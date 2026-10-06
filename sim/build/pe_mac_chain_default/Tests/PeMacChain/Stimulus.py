"""
Tests/PeMacChain/Stimulus.py
Input sequence for pe_input_mux → mac_q16 chain.
Reuses mux stimulus since mux is the chain entry point.
"""

from Engine.Generators import VectorConfig
from Engine.TestScenario import StimulusConfig
from Components.MuxNode import MUX_INPUT_SPEC, MUX_PLACEMENTS

DEFAULT = StimulusConfig(
    name        = "pe_mac_chain_default",
    signal_spec = MUX_INPUT_SPEC,
    vectors     = VectorConfig(
        random_count      = 200,
        seed              = 42,
        first_idle_cycles = 0,
        drain_cycles      = 8,   # mux(2) + mac(4) + margin
    ),
    placements  = MUX_PLACEMENTS,
)
