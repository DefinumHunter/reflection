"""mac_q16 test: the whole chain in one place.

    Protocol  -> how a transaction looks in clocks
    Scenario  -> rules, weights, directed cases
    PLAN      -> what runs, in order
    RTL and Reflection come from Project (hardware/, Components/)
    COMPARE   -> how expected and actual are compared each clock
"""
from Engine.Generator import Directed, Random
from . import Checks, Protocol, Scenario
from .Protocol import Reset

SEED = 1
IDLE = Protocol.IDLE
RULES = Scenario.RULES

PLAN = [
    Directed([Reset(5)]),
    Directed(Scenario.DIRECTED),
    Random(Scenario.WEIGHTS, count=250),
    Directed([Reset(3)]),                 # reset in the middle of the stream
    Random(Scenario.WEIGHTS, count=250),
]

COMPARE = Checks.compare
