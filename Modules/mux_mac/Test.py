"""First structural integration: mux -> mac; no composite golden."""
from Engine.Generator import Directed,Random
from Engine.Rules import one_of
from . import Checks,Coverage,Protocol,Scenario
from .Protocol import Direct,PreSum,Reset

SEED=45
IDLE=Protocol.IDLE
RULES=Scenario.RULES
GAP=one_of([0,1,2,4],weights=[8,3,2,1])
PLAN=[
 Directed([Reset(5)]),
 Directed(Scenario.DIRECTED),
 Random(Scenario.WEIGHTS,count=500,gap=0),
 Directed([PreSum(a=0x7FFFFFFF,b=1,c=0x7FFFFFFF,sub_pre=0,id=15,ring_final=1,sub_post=1),
           Reset(4),Direct(a=0x10000,b=0x20000,id=1)]),
 Random(Scenario.WEIGHTS,count=600,gap=GAP),
 Directed([Reset(3)]),
 Random(Scenario.WEIGHTS,count=300,gap=0),
]
COMPARE=Checks.compare
COVERAGE=Coverage.POINTS
