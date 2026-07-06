"""
run.py
Single entry point. Lives at repo root.

Reads TEST_PLAN from each module's Build.py.
Runs five stages for each TestScenario.

Usage:
    python run.py --module mac_q16
    python run.py --module all
    python run.py --module mac_q16 --sim questa
    python run.py --module mac_q16 --waves
    python run.py --plan plan.py
"""

import argparse
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT    = Path(__file__).resolve().parent
SIM_DIR = ROOT / "sim"
RTL_DIR = ROOT / "rtl"
TB_DIR  = ROOT / "tb"
RES_DIR = SIM_DIR / "Results"

sys.path.insert(0, str(SIM_DIR))
sys.path.insert(0, str(ROOT))

from config import SIMULATORS, ACTIVE_SIM, SimConfig
from cocotb_tools.runner import get_runner
from Engine.Scoreboard import save, load, compare
from Engine.Generators import generate_stream
from Engine.ArchBase import build_reference


# ── Module registry ───────────────────────────────────────────────

MODULES = {
    "mac_q16":      "Tests.MacQ16.Build",
    "pe_input_mux": "Tests.PeInputMux.Build",
    "pe_mac_chain": "Tests.PeMacChain.Build",
}


# ── Stage 1+2+3: precompute ───────────────────────────────────────

def precompute(scenario) -> bool:
    """Stages 1, 2, 3 — pure Python, no cocotb."""
    name = scenario.name
    print(f"\n{'='*20} PRECOMPUTE: {name} {'='*20}")

    # Stage 1 — build reference
    ref = build_reference(scenario.nodes, scenario.edges)

    # Stage 2 — generate and save stream
    stream = generate_stream(
        scenario.stimulus.signal_spec,
        scenario.stimulus.vectors,
        scenario.stimulus.placements,
    )
    stream_path = RES_DIR / f"{name}_stream.csv"
    save(stream_path, stream)
    print(f"  stream    : {len(stream)} cycles → {stream_path.name}")

    # Stage 3 — run reference, save expected
    expected = [{"cycle": i, **ref(inp)} for i, inp in enumerate(stream)]
    expected_path = RES_DIR / f"{name}_expected.csv"
    save(expected_path, expected)
    print(f"  expected  : {len(expected)} cycles → {expected_path.name}")

    return True


# ── Stage 4: simulate ─────────────────────────────────────────────

def simulate(scenario, sim: SimConfig, waves: bool) -> bool:
    """Stage 4 — compile RTL and run cocotb."""
    name      = scenario.name
    build_dir = SIM_DIR / "build" / name

    # Clean stale Python files
    if build_dir.exists():
        for f in build_dir.rglob("*.py"):  f.unlink()
        for f in build_dir.rglob("*.pyc"): f.unlink()
    build_dir.mkdir(parents=True, exist_ok=True)

    # Copy sim tree into build dir
    for src in SIM_DIR.rglob("*.py"):
        if "build" in src.parts:
            continue
        dst = build_dir / src.relative_to(SIM_DIR)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # Find which test folder owns this scenario and copy Simulate.py
    # Convention: scenario.name starts with module name
    module_name = next(
        (m for m in MODULES if scenario.name.startswith(m)), None
    )
    if module_name:
        pascal = "".join(w.capitalize() for w in module_name.split("_"))
        sim_src = SIM_DIR / "Engine" / "Simulate.py"
        if sim_src.exists():
            shutil.copy2(sim_src, build_dir / f"test_{module_name}.py")

    # Set up environment
    env = {**os.environ, **sim.extra_env}
    if sim.tool_path and str(sim.tool_path):
        env["PATH"] = str(sim.tool_path) + os.pathsep + env.get("PATH", "")
    os.environ.update(env)

    if sim.module_load:
        subprocess.run(f"module load {sim.module_load}", shell=True)

    print(f"\n{'='*20} BUILD: {name} {'='*20}")
    runner = get_runner(sim.name)

    try:
        sources = [RTL_DIR / s for s in scenario.rtl_sources]
        sources.append(TB_DIR / f"{scenario.hdl_top}.sv")
        runner.build(
            sources      = sources,
            hdl_toplevel = scenario.hdl_top,
            always       = True,
            build_dir    = build_dir,
            build_args   = sim.build_args,
        )
    except subprocess.CalledProcessError:
        print(f"\n{'='*20} BUILD FAILED {'='*20}")
        log = build_dir / "build.log"
        print(log.read_text() if log.exists() else "No build log found.")
        return False

    print(f"\n{'='*20} SIMULATE: {name} {'='*20}")
    test_module = f"test_{module_name}" if module_name else f"test_{name}"
    runner.test(
        hdl_toplevel = scenario.hdl_top,
        test_module  = test_module,
        build_dir    = build_dir,
        extra_env    = {
            "COCOTB_RESOLVE_X": "ZEROS",
            "SCENARIO_NAME":    scenario.name,
            **sim.extra_env
        },
        waves        = waves,
    )

    if waves:
        _open_waves(build_dir, sim)

    return True


# ── Stage 5: scoreboard ───────────────────────────────────────────

def scoreboard(scenario) -> bool:
    """Stage 5 — compare expected vs actual."""
    name = scenario.name
    print(f"\n{'='*20} SCOREBOARD: {name} {'='*20}")

    expected_path = RES_DIR / f"{name}_expected.csv"
    actual_path   = RES_DIR / f"{name}_actual.csv"

    if not actual_path.exists():
        print(f"❌  Actual results not found: {actual_path}")
        return False

    expected = load(expected_path)
    actual   = load(actual_path)

    # Apply filter from CheckConfig
    chk = scenario.checks
    if chk.filter == "valid_only":
        expected = [r for r in expected if r.get("out_vld", 0) == 1]
        actual   = [r for r in actual   if r.get("out_vld", 0) == 1]

    return compare(
        expected = expected,
        actual   = actual,
        signals  = chk.signals,
        name     = name,
    )


# ── Orchestrator ──────────────────────────────────────────────────

def run_scenario(scenario, sim: SimConfig, waves: bool) -> bool:
    if not precompute(scenario):
        return False
    if not simulate(scenario, sim, waves):
        return False
    return scoreboard(scenario)


def run_module(module_name: str, sim: SimConfig, waves: bool) -> bool:
    pkg  = importlib.import_module(MODULES[module_name])
    plan = pkg.TEST_PLAN
    failed = []
    for scenario in plan:
        if not run_scenario(scenario, sim, waves):
            failed.append(scenario.name)
    return len(failed) == 0


# ── Waveform viewer ───────────────────────────────────────────────

def _open_waves(build_dir: Path, sim: SimConfig):
    wave_map  = {"vcd": "waves.vcd", "fsdb": "waves.fsdb", "wlf": "vsim.wlf"}
    wave_file = build_dir / wave_map.get(sim.wave_format, "waves.vcd")
    if not wave_file.exists():
        print(f"[WARNING] waveform not found: {wave_file}")
        return
    viewer = Path(sim.wave_viewer)
    if not viewer.exists() and not shutil.which(str(viewer)):
        print(f"[WARNING] wave viewer not found: {viewer}")
        return
    subprocess.Popen([str(viewer), str(wave_file)])


# ── CLI ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run RTL verification — five stages."
    )
    parser.add_argument("--module", default=None,
        help=f"Module name or 'all'. Available: {', '.join(MODULES)}")
    parser.add_argument("--plan", default=None,
        help="Path to plan.py file listing modules to run")
    parser.add_argument("--sim", default=ACTIVE_SIM,
        choices=list(SIMULATORS))
    parser.add_argument("--waves", action="store_true")
    args = parser.parse_args()

    sim = SIMULATORS[args.sim]

    # determine which modules to run
    if args.plan:
        plan_path = Path(args.plan)
        spec = importlib.util.spec_from_file_location("plan", plan_path)
        plan_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plan_mod)
        targets = plan_mod.PLAN
    elif args.module == "all":
        targets = list(MODULES.keys())
    elif args.module in MODULES:
        targets = [args.module]
    elif args.module:
        print(f"[ERROR] Unknown module '{args.module}'")
        sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    failed = []
    for mod in targets:
        if not run_module(mod, sim, args.waves):
            failed.append(mod)

    print()
    if failed:
        print(f"❌  Failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("✅  All done.")


if __name__ == "__main__":
    main()
