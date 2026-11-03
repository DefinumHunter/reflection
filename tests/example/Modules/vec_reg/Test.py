"""vec_reg: worked example for array ports."""
from Engine.Generator import Directed, Random
from . import Checks, Coverage, Protocol, Scenario
from .Protocol import Reset

SEED = 1
IDLE = Protocol.IDLE
RULES = Scenario.RULES
PLAN = [Directed([Reset()]), Directed(Scenario.DIRECTED), Random(Scenario.WEIGHTS, count=40, gap=1)]
COMPARE = Checks.compare
COVERAGE = Coverage.POINTS
