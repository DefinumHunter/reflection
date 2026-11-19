"""Full PE: dense streams, mixed pre-sums, neighbor errors, and resets.

No composite golden model: Reflection builds it from the three RTL leaves.
The stimulus timing targets PIPELINE_STAGES=4.
"""
from Engine.Generator import Directed, Random
from . import Checks, Coverage, Protocol, Scenario
from .Protocol import Direct, Local, PreSum, Reset, packed_gap, spaced_gap

SEED = 47
IDLE = Protocol.IDLE
RULES = Scenario.RULES

PLAN = [
    Directed([Reset(5)]),
    Directed(Scenario.DIRECTED, gap=packed_gap),
    Random(Scenario.WEIGHTS, count=450, gap=packed_gap),
    Directed([
        PreSum(a=0x7FFFFFFF, b=1, c=0x10000, sub_pre=0,
               neighbor=0x7FFFFFFF, id=15, ring_final=1, sub_post=0),
        Reset(4),
        Direct(a=0x10000, b=0x20000, neighbor=0, id=1),
    ], gap=packed_gap),
    Random(Scenario.WEIGHTS, count=650, gap=spaced_gap),
    Directed([Reset(3)]),
    Random(Scenario.WEIGHTS, count=350, gap=packed_gap),
]

COMPARE = Checks.compare
COVERAGE = Coverage.POINTS
