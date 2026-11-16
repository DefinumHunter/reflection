"""Executable verification plan for the current mac_q16 RTL.

The reference model is Components/mac_q16_node.py, discovered by Project.
No changes to Engine, RTL, TB, or the golden model are required.
"""
from Engine.Generator import Directed, Random
from Engine.Rules import one_of
from . import Checks, Coverage, Protocol, Scenario
from .Protocol import Mac, Reset

SEED = 42
IDLE = Protocol.IDLE
RULES = Scenario.RULES

# Gaps are between beats, not a handshake: mac_q16 has no ready input.
# Two uninterrupted streams stress pipeline alignment; random gaps exercise
# bubbles and busy deassertion. Reset cuts off in-flight valid operations.
GAP = one_of([0, 1, 2, 4], weights=[8, 3, 2, 1])

PLAN = [
    Directed([Reset(5)]),
    Directed(Scenario.DIRECTED),
    Random(Scenario.WEIGHTS, count=400, gap=0),
    Directed([Mac(a=0x7FFFFFFF, b=0x7FFFFFFF, vld=1, id=15),
              Mac(a=0x80000000, b=0x7FFFFFFF, vld=1, id=14),
              Reset(3)]),
    Random(Scenario.WEIGHTS, count=500, gap=GAP),
    Directed([Reset(2)]),
    Random(Scenario.WEIGHTS, count=200, gap=0),
]

COMPARE = Checks.compare
COVERAGE = Coverage.POINTS
