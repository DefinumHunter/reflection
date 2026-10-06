"""pe_mac_wrapper test: the whole chain in one place.

    Protocol  -> how a transaction looks in clocks
    Scenario  -> rules, weights, gaps, directed cases
    PLAN      -> what runs, in order
    RTL and Reflection come from Project (hardware/, Components/, Connections.json)
    COMPARE   -> how expected and actual are compared each clock
    COVERAGE  -> what is counted to know what the run actually exercised
"""
from Engine.Generator import Directed, Random
from . import Checks, Coverage, Protocol, Scenario
from .Protocol import Reset

SEED = 1
IDLE = Protocol.IDLE
RULES = Scenario.RULES

PLAN = [
    Directed([Reset(5)]),
    Directed(Scenario.DIRECTED, gap=0),
    Directed(Scenario.BACK_TO_BACK, gap=-1),
    Random(Scenario.WEIGHTS, count=200, gap=Scenario.GAP),
    Directed([Reset(2)], gap=1),
    Random(Scenario.WEIGHTS, count=100, gap=Scenario.GAP),
]

COMPARE = Checks.compare
COVERAGE = Coverage.POINTS
