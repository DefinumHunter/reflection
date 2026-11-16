"""Input scenarios with explicit Q16.16 integration corners."""
from Modules.pe_input_mux.Scenario import RULES, WEIGHTS, DIRECTED as MUX_DIRECTED
from .Protocol import Direct, Local, PreSum

DIRECTED = [
 Direct(a=0x10000,b=0x10000,id=1,ring_final=0,sub_post=0),
 Direct(a=0xFFFF0000,b=0x10000,id=2,ring_final=1,sub_post=1),
 Local(a=0x20000,local=0x30000,id=3,ring_final=1,sub_post=0),
 PreSum(a=0x10000,b=0x20000,c=0x30000,sub_pre=0,id=4,ring_final=0,sub_post=1),
 PreSum(a=0x30000,b=0x10000,c=0x20000,sub_pre=1,id=5,ring_final=1,sub_post=1),
 PreSum(a=0x7FFFFFFF,b=1,c=0x10000,sub_pre=0,id=6),
 PreSum(a=0x80000000,b=1,c=0x10000,sub_pre=1,id=7),
 Direct(a=1,b=0x8000,id=8),
 Direct(a=3,b=0x8000,id=9),
 Direct(a=5,b=0x8000,id=10),
 Direct(a=0x7FFFFFFF,b=0x7FFFFFFF,id=11),
 Direct(a=0x80000000,b=0x7FFFFFFF,id=12),
 Direct(a=0xDEADBEEF,b=0x12345678,issue=0,id=13),
] + MUX_DIRECTED
