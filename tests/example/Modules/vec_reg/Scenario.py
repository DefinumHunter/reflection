from Engine.Rules import bits
from .Protocol import Lanes

RULES = {
    "a": lambda ctx: [ctx.rng.getrandbits(8) for _ in range(3)],
    "k": bits(8),
}
WEIGHTS = {Lanes: 1}
DIRECTED = [Lanes(a=[1, 2, 3], k=0), Lanes(a=[255, 255, 255], k=1)]
