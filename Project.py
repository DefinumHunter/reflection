"""The one place that knows where everything lives.

Everything else asks this file for sources, components and models instead of
building paths itself. If the project layout changes, only this file changes.

    import Project
    m = Project.model("pe_mac_wrapper")                   # parse + check + build
    m = Project.model("mac_q16", params={"PIPELINE_STAGES": 6})
    rows = Project.stimulus("pe_mac_wrapper", m.netlist)   # Modules/<m>/Test.py
"""
import importlib
from functools import lru_cache
from pathlib import Path

from Engine.Connections import check_file
from Engine.Core import find_leaves
from Engine.Coverage import Coverage
from Engine.Generator import Generator
from Engine.Model import Model
from Engine.Netlist import load

ROOT = Path(__file__).resolve().parent

HARDWARE = ROOT / "hardware"
RTL_DIR = HARDWARE / "rtl"        # every .sv here is compiled together
TB_DIR = HARDWARE / "tb"          # one TB per module, only the used one is compiled
COMPONENTS = "Components"         # Python package with the LeafSpecs
MODULES_DIR = ROOT / "Modules"    # per-module verification files (Connections.json, ...)

CLOCKS = ("clk",)

# module under test -> its TB module (file TB_DIR/<tb>.sv)
MODULES = {
    "mac_q16":        "tb_mac_q16",
    "pe_mac_wrapper": "tb_pe_mac_wrapper",
}


def tb(module: str) -> str:
    if module not in MODULES:
        raise KeyError(f"unknown module '{module}'; known: {sorted(MODULES)}")
    return MODULES[module]


def rtl_sources() -> list:
    return sorted(RTL_DIR.glob("*.sv"))


def sources(module: str) -> list:
    return rtl_sources() + [TB_DIR / f"{tb(module)}.sv"]


@lru_cache(maxsize=None)
def components() -> dict:
    return find_leaves(COMPONENTS)


def connections_file(module: str):
    path = MODULES_DIR / module / "Connections.json"
    return path if path.exists() else None


def netlist(module: str, params=None, check_connections=True, files=None):
    """files: override the source list (e.g. a deliberately broken RTL copy)."""
    nl = load(files or sources(module), tb(module), components(), CLOCKS, params)
    conn = connections_file(module)
    if check_connections and conn is not None:
        check_file(nl, conn)
    return nl


def model(module: str, params=None, init=None, check_connections=True, files=None) -> Model:
    return Model(netlist(module, params, check_connections, files), components(), init)


def test(module: str):
    """Modules/<module>/Test.py: SEED, IDLE, RULES, PLAN, COMPARE, COVERAGE."""
    tb(module)
    return importlib.import_module(f"{MODULES_DIR.name}.{module}.Test")


def stimulus(module: str, netlist, seed=None) -> Generator:
    """Iterable of rows ({TB input: value}, one per clock) from the module's Test.py.
    seed=None uses the test's own SEED."""
    t = test(module)
    return Generator(t.PLAN, t.RULES, t.IDLE, list(netlist.inputs), netlist.widths,
                     t.SEED if seed is None else seed)


def coverage(module: str):
    """Fresh coverage counters for the module's COVERAGE points, or None if
    its Test.py does not list any."""
    points = getattr(test(module), "COVERAGE", None)
    return Coverage(points) if points else None


def dry_run(module: str, seed=None, params=None, tail=20) -> dict:
    """The module's test on the model only, no simulator: returns the coverage
    data. Fast (well under a second), for tuning scenarios and coverage."""
    m = model(module, params=params)
    stim = stimulus(module, m.netlist, seed)
    cov = coverage(module)
    if cov is None:
        raise ValueError(f"Modules/{module}/Test.py has no COVERAGE")
    idle = test(module).IDLE
    for row in stim:
        m.step(row)
        cov.sample_tags(m.tags)
    for _ in range(tail):
        m.step(idle)
        cov.sample_tags(m.tags)
    cov.sample_ops(stim.sent)
    return cov.data()
