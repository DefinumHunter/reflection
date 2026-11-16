"""Pipelined integration: one MAC input each clock at full throughput.

MacNeighbor lasts five clocks, but starts can overlap by four clocks.
Its neighbor arrives on the fifth clock, alongside later MAC inputs.
This plan targets the default PIPELINE_STAGES=4.
"""
from Engine.Generator import Directed, Random
from Engine.Rules import one_of
from . import Checks, Coverage, Protocol, Scenario
from .Protocol import MacNeighbor, Reset

SEED = 46
IDLE = Protocol.IDLE
RULES = Scenario.RULES

# A five-cycle transaction starting four clocks before the previous one ends
# gives one new MAC input per clock. Smaller overlap inserts bubbles.
FULL_RATE = -Protocol.PIPELINE_STAGES
GAP = one_of([FULL_RATE, FULL_RATE + 1, FULL_RATE + 2, 0],
             weights=[8, 3, 2, 1])

PLAN = [
    Directed([Reset(5)]),
    Directed(Scenario.DIRECTED, gap=FULL_RATE),
    Random(Scenario.WEIGHTS, count=350, gap=FULL_RATE),
    Directed([
        MacNeighbor(a=0x10000, b=0x10000, neighbor=0x7FFFFFFF,
                    id=15, ring_final=1, sub_post=0, mismatch=1),
        Reset(4),
        MacNeighbor(a=0x10000, b=0x10000, neighbor=0, id=1),
    ], gap=FULL_RATE),
    Random(Scenario.WEIGHTS, count=500, gap=GAP),
    Directed([Reset(3)]),
    Random(Scenario.WEIGHTS, count=200, gap=FULL_RATE),
]

COMPARE = Checks.compare
COVERAGE = Coverage.POINTS
