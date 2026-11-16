"""Integration plan: MAC output and aligned neighbor -> strapping.

The stimulus protocol is timed for PIPELINE_STAGES=4. Use the default
parameter for this test; alternate depths require changing that timing.
"""
from Engine.Generator import Directed, Random
from Engine.Rules import one_of
from . import Checks, Coverage, Protocol, Scenario
from .Protocol import MacNeighbor, Reset

SEED = 46
IDLE = Protocol.IDLE
RULES = Scenario.RULES
GAP = one_of([0, 1, 2, 4], weights=[8, 3, 2, 1])

PLAN = [
    Directed([Reset(5)]),
    Directed(Scenario.DIRECTED),
    Random(Scenario.WEIGHTS, count=350, gap=0),
    Directed([
        MacNeighbor(a=0x10000, b=0x10000, neighbor=0x7FFFFFFF,
                    id=15, ring_final=1, sub_post=0, mismatch=1),
        Reset(4),
        MacNeighbor(a=0x10000, b=0x10000, neighbor=0, id=1),
    ]),
    Random(Scenario.WEIGHTS, count=500, gap=GAP),
    Directed([Reset(3)]),
    Random(Scenario.WEIGHTS, count=200, gap=0),
]

COMPARE = Checks.compare
COVERAGE = Coverage.POINTS
