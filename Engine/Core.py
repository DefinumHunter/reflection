"""Python half of an RTL module.

The RTL gives us structure (ports, nets, instances). The Python side gives
what the RTL parser cannot see inside a leaf module: its behaviour (golden)
and, for each output, whether it waits for the clock.
"""
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class LeafSpec:
    """Behaviour of one RTL module.

    module : RTL module name; every instance of that module gets this spec.

    golden : factory called once per RTL instance as golden(**params, **init),
             where params are the instance's elaborated RTL parameters
             (e.g. PIPELINE_STAGES=4) and init is optional per-instance
             state override (e.g. a pre-filled pipeline). The returned object:

             tick(inputs) -> dict   called exactly once per clk, after all of
                                    the instance's inputs have settled.
                                    Must return every RTL output port.
             start() -> dict        optional. Values of waiting outputs at
                                    cycle 0. Without it they start as None (X).

    comb   : outputs that do NOT wait: the value tick() returns is visible in
             the same cycle. Every other output waits: the value tick()
             returns becomes visible at the start of the next cycle.
             Longer latency is the golden's own business (its own pipeline).

    input_specs / output_specs: SignalSpec dicts for stimulus generation.
             The model does not use them; ports come from the RTL.
    """
    module: str
    input_specs: dict
    output_specs: dict
    golden: Callable[..., Any]
    comb: frozenset = field(default_factory=frozenset)

    def __post_init__(self):
        object.__setattr__(self, "comb", frozenset(self.comb))


def find_leaves(package: str) -> dict:
    """Import every module of a package (e.g. "Components") and collect the
    LeafSpec objects defined in it, keyed by RTL module name."""
    import importlib
    import pkgutil

    pkg = importlib.import_module(package)
    found = {}
    for info in pkgutil.iter_modules(pkg.__path__):
        mod = importlib.import_module(f"{package}.{info.name}")
        for obj in vars(mod).values():
            if isinstance(obj, LeafSpec):
                other = found.get(obj.module)
                if other is not None and other is not obj:
                    raise ValueError(f"two LeafSpecs for RTL module '{obj.module}' in {package}")
                found[obj.module] = obj
    return found
