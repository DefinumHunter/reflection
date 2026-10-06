"""
Tests/MacQ16/Stimulus.py
Input sequence definitions for mac_q16.
One StimulusConfig = one complete stimulus scenario.
Add more named configs below for additional test variants.
"""

from Engine.Generators import VectorConfig
from Engine.TestScenario import StimulusConfig
from Components.MacNode import MAC_INPUT_SPEC, MAC_PLACEMENTS

# ── Default stimulus ──────────────────────────────────────────────
# Corner cases pinned at start, random vectors with gaps,
# one directed valid-drop race sequence at a random position.

DEFAULT = StimulusConfig(
    name        = "mac_q16_default",
    signal_spec = MAC_INPUT_SPEC,
    vectors     = VectorConfig(
        random_count      = 200,
        seed              = 42,
        first_idle_cycles = 0,
        drain_cycles      = 6,
    ),
    placements  = MAC_PLACEMENTS,
)
