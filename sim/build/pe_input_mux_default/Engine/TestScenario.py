"""
Engine/TestScenario.py
Pure data container. No cocotb, no RTL, no execution logic.

TestScenario — one complete test: architecture + stimulus + checks.
StimulusConfig — what to feed into the circuit.
CheckConfig    — what to compare and how.
"""

from dataclasses import dataclass, field


@dataclass
class StimulusConfig:
    """
    Defines one complete input sequence.
    One file = one scenario. Create more files for more scenarios.

    signal_spec — { name: SignalSpec } — what signals and random rules
    vectors     — VectorConfig — counts, seed, gap behavior
    placements  — list of Placement — corner cases and positions
    name        — identifier used in result file names
    """
    name:        str
    signal_spec: dict
    vectors:     object   # VectorConfig
    placements:  list     = field(default_factory=list)


@dataclass
class CheckConfig:
    """
    Defines what to verify and how.
    One file = one check scenario.

    signals — list of signal names to compare in scoreboard
    filter  — "all"        : compare every cycle
              "valid_only" : compare only cycles where out_vld=1
    name    — identifier used in result file names
    """
    name:    str
    signals: list
    filter:  str = "all"   # "all" or "valid_only"


@dataclass
class TestScenario:
    """
    One complete test run — combines architecture, stimulus, and checks.
    Lives in Build.py. run.py receives a list of these.

    name     — unique name for this scenario, used in result files
    nodes    — list of NodeDef — from Wiring.py
    edges    — list of edges  — from Wiring.py
    duts     — { node_name: dut_handle } — filled by run.py at sim time
    stimulus — StimulusConfig
    checks   — CheckConfig
    hdl_top  — testbench top-level module name
    rtl_sources — list of RTL file paths to compile
    """
    name:        str
    nodes:       list
    edges:       list
    stimulus:    StimulusConfig
    checks:      CheckConfig
    hdl_top:     str
    rtl_sources: list     = field(default_factory=list)
    duts:        dict     = field(default_factory=dict)  # filled at runtime
