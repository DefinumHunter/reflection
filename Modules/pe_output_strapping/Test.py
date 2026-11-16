"""Standalone verification of pe_output_strapping.

Default CHECK_NEIGHBOR=1 checks dropped bad transactions and sticky error.
Run again with CHECK_NEIGHBOR=0 for first-PE bypass behavior.
"""
from Engine.Generator import Directed, Random
from Engine.Rules import one_of
from . import Checks, Coverage, Protocol, Scenario
from .Protocol import Beat, Reset

SEED = 44
IDLE = Protocol.IDLE
RULES = Scenario.RULES
GAP = one_of([0, 1, 2, 4], weights=[8, 3, 2, 1])

PLAN = [
    Directed([Reset(4)]),
    Directed(Scenario.DIRECTED),
    Random(Scenario.WEIGHTS, count=400, gap=0),
    Directed([
        Beat(mac=0x7FFFFFFF, neighbor=0x7FFFFFFF, id=15,
             ring_final=1, sub_post=0, mismatch=1),
        Reset(3),
        Beat(mac=0x80000000, neighbor=0x80000000, id=1,
             ring_final=0, sub_post=0),
    ]),
    Random(Scenario.WEIGHTS, count=500, gap=GAP),
    Directed([Reset(2)]),
    Random(Scenario.WEIGHTS, count=200, gap=0),
]

COMPARE = Checks.compare
COVERAGE = Coverage.POINTS
