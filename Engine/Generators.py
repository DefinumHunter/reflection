# STAND-IN. Replace with the real Engine/Generators.py.
# Only here so Components/MacNode.py imports; the model does not use it.
from dataclasses import dataclass, field


@dataclass
class SignalSpec:
    kind: str = "data"
    width: int = 32
    signed: bool = False
    corner_pool: list = field(default_factory=list)
    corner_probability: float = 0.0
    prob_one: float = 0.5


@dataclass
class Placement:
    pass
