"""Executable pe_input_mux verification plan; RTL and golden are unchanged."""
from Engine.Generator import Directed, Random
from Engine.Rules import one_of
from . import Checks, Coverage, Protocol, Scenario
from .Protocol import Direct, Local, PreSum, Reset

SEED = 43
IDLE = Protocol.IDLE
RULES = Scenario.RULES
GAP = one_of([0, 1, 2, 4], weights=[8, 3, 2, 1])

PLAN = [
    Directed([Reset(4)]),
    Directed(Scenario.DIRECTED),
    Random(Scenario.WEIGHTS, count=400, gap=0),
    Directed([PreSum(a=0x7FFFFFFF, b=1, c=0x80000000,
                     sub_pre=0, id=15, ring_final=1, sub_post=1),
              Reset(3)]),
    Random(Scenario.WEIGHTS, count=500, gap=GAP),
    Directed([Reset(2)]),
    Random(Scenario.WEIGHTS, count=200, gap=0),
]

COMPARE = Checks.compare
COVERAGE = Coverage.POINTS
