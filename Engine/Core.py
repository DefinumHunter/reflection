"""Python half of an RTL module.

The RTL gives us structure (ports, nets, instances). The Python side gives
what the RTL parser cannot see inside a leaf module: its behaviour (golden)
and, for each output, whether it waits for the clock.

One file per RTL module, found by name, nothing to register:

    hardware/rtl/pe_input_mux.sv      ->   Components/pe_input_mux_node.py
                                           NODE = LeafSpec(golden=PeInputMux)
"""
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class LeafSpec:
    """Behaviour of one RTL module.

    golden : factory called once per RTL instance as golden(**params, **init),
             where params are the instance's elaborated RTL parameters
             (e.g. PIPELINE_STAGES=4) and init is optional per-instance
             state override (e.g. a pre-filled pipeline). The returned object:

             tick(inputs) -> dict   called exactly once per clk, after all of
                                    the instance's inputs have settled.
                                    Must return every RTL output port.
             start() -> dict        optional. Values of waiting outputs at
                                    cycle 0. Without it they start as None (X).
             tags                   optional list. The golden appends a name
                                    whenever it takes a branch worth counting
                                    ("sat_pos"); the model collects and clears
                                    it after every tick, for coverage.

    comb   : outputs that do NOT wait: the value tick() returns is visible in
             the same cycle. Every other output waits: the value tick()
             returns becomes visible at the start of the next cycle.
             Longer latency is the golden's own business (its own pipeline).

    module : RTL module name. Not written in a component file: it comes from
             the file name (Components/<module>_node.py). Tests that build
             specs by hand may set it.
    """
    golden: Callable[..., Any]
    comb: frozenset = field(default_factory=frozenset)
    module: str = None

    def __post_init__(self):
        object.__setattr__(self, "comb", frozenset(self.comb))


SUFFIX = "_node"


def find_leaves(package: str) -> dict:
    """Components of a package (e.g. "Components"), keyed by RTL module name.

    Only files named <module>_node.py are components; the RTL module is the
    file name without "_node", and the spec is the file's NODE. Other files
    in the package (shared helpers) are not imported here.
    """
    import dataclasses
    import importlib
    import pkgutil

    pkg = importlib.import_module(package)
    found = {}
    for info in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda m: m.name):
        if not info.name.endswith(SUFFIX):
            continue
        module = info.name[:-len(SUFFIX)]
        where = f"{package}/{info.name}.py"
        mod = importlib.import_module(f"{package}.{info.name}")
        spec = getattr(mod, "NODE", None)
        if not isinstance(spec, LeafSpec):
            raise ValueError(f"{where}: needs NODE = LeafSpec(golden=..., comb=...)")
        if spec.module not in (None, module):
            raise ValueError(f"{where}: NODE says module='{spec.module}', but the file "
                             f"name says '{module}'; drop module=, the file name decides")
        found[module] = dataclasses.replace(spec, module=module)
    return found
