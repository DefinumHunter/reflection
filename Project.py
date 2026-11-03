"""The one place that knows where everything lives.

Everything else asks this file for sources, components and models instead of
building paths itself. If the project layout changes, only this file changes.

    import Project
    m = Project.model("w_normalize")                      # parse + check + build
    m = Project.model("mac_q16", params={"PIPELINE_STAGES": 6})
    rows = Project.stimulus("w_normalize", m.netlist)      # Modules/<m>/Test.py

The project root is this folder. Setting REFLECTION_ROOT points it at another
folder with the same layout (hardware/, Components/, Modules/); the tests use
that for the worked example in tests/example/. The engine always comes from here.
"""
import importlib
import importlib.util
import os
import sys
from functools import lru_cache
from pathlib import Path

from Engine.Connections import check_file
from Engine.Core import find_leaves
from Engine.Coverage import Coverage
from Engine.Generator import Generator
from Engine.Model import Model
from Engine.Netlist import load

ENGINE_ROOT = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("REFLECTION_ROOT") or ENGINE_ROOT).resolve()
if ROOT != ENGINE_ROOT:
    # its Components/ and Modules/ packages, not ours, whatever sys.path says
    for _pkg in ("Components", "Modules"):
        _spec = importlib.util.spec_from_file_location(
            _pkg, ROOT / _pkg / "__init__.py", submodule_search_locations=[str(ROOT / _pkg)])
        sys.modules[_pkg] = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(sys.modules[_pkg])

HARDWARE = ROOT / "hardware"
RTL_DIR = HARDWARE / "rtl"        # every .sv here is compiled together
TB_DIR = HARDWARE / "tb"          # tb_<module>.sv, only the used one is compiled
COMPONENTS = "Components"         # Python package with the LeafSpecs
MODULES_DIR = ROOT / "Modules"    # Modules/<module>/: the module's test

CLOCKS = ("clk",)


def modules() -> list:
    """Modules that have a test: every Modules/<module>/ with a Test.py."""
    return sorted(p.parent.name for p in MODULES_DIR.glob("*/Test.py"))


def tb(module: str) -> str:
    """TB module of a module under test: tb_<module>, or TB = "..." in its Test.py."""
    if module not in modules():
        raise KeyError(f"unknown module '{module}': no Modules/{module}/Test.py; "
                       f"known: {modules()}")
    return getattr(test(module), "TB", f"tb_{module}")


def rtl_sources() -> list:
    return sorted(RTL_DIR.glob("*.sv"))


def sources(module: str) -> list:
    path = TB_DIR / f"{tb(module)}.sv"
    if not path.exists():
        raise FileNotFoundError(f"no TB for '{module}': expected {path}")
    return rtl_sources() + [path]


def rtl_modules() -> list:
    """Names of the modules declared in hardware/rtl/*.sv."""
    from pyslang import syntax
    names = []
    for f in rtl_sources():
        tree = syntax.SyntaxTree.fromFile(str(f))   # keep it alive while reading its nodes
        for m in tree.root.members:
            if m.kind == syntax.SyntaxKind.ModuleDeclaration:
                names.append(m.header.name.valueText)
    return names


@lru_cache(maxsize=None)
def components() -> dict:
    """{RTL module: LeafSpec} from Components/<module>_node.py."""
    found = find_leaves(COMPONENTS)
    unknown = sorted(set(found) - set(rtl_modules()))
    if unknown:
        files = ", ".join(f"{COMPONENTS}/{m}_node.py" for m in unknown)
        raise ValueError(f"{files}: no such module in {RTL_DIR.relative_to(ROOT)} "
                         f"(typo in the file name?)")
    return found


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
    """Modules/<module>/Test.py: SEED, IDLE, RULES, PLAN, COMPARE, COVERAGE (, TB)."""
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
