"""
Tests/PeInputMux/Stimulus.py
Input sequence definitions for pe_input_mux.
"""

from Engine.Generators import VectorConfig
from Engine.TestScenario import StimulusConfig
from Components.MuxNode import MUX_INPUT_SPEC, MUX_PLACEMENTS

DEFAULT = StimulusConfig(
    name        = "pe_input_mux_default",
    signal_spec = MUX_INPUT_SPEC,
    vectors     = VectorConfig(
        random_count      = 200,
        seed              = 42,
        first_idle_cycles = 0,
        drain_cycles      = 4,
    ),
    placements  = MUX_PLACEMENTS,
)
