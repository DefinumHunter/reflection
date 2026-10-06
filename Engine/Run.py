"""Build and run the UVM test for one module in Icarus, no make needed.

    python -m Engine.Run pe_mac_wrapper
    python -m Engine.Run mac_q16 PIPELINE_STAGES=6
    python -m Engine.Run pe_mac_wrapper seed=1234     (reproduce a failing run)
    python -m Engine.Run pe_mac_wrapper seeds=20      (seeds 1..20, coverage merged)

Returns / exits with the number of failed tests (0 = pass).
The coverage of the last run is in sim_build/<module>/coverage.json.
"""
import json
import os
import sys
from pathlib import Path

from cocotb_tools.runner import get_results, get_runner

import Project
from Engine import Coverage


def run(module, params=None, sources=None, tail=20, waves=False, build_dir=None, seed=None):
    """sources: override the file list (e.g. a deliberately broken RTL copy).
    seed: override the test's SEED."""
    params = params or {}
    tb = Project.tb(module)
    build_dir = build_dir or Project.ROOT / "sim_build" / module
    runner = get_runner("icarus")
    runner.build(sources=sources or Project.sources(module), hdl_toplevel=tb,
                 parameters=params, build_dir=build_dir, always=True, waves=waves)
    env = {"REFLECTION_MODULE": module,
           "REFLECTION_PARAMS": json.dumps(params),
           "REFLECTION_TAIL": str(tail),
           **({"REFLECTION_SEED": str(seed)} if seed is not None else {}),
           "REFLECTION_COVERAGE": str(Path(build_dir) / "coverage.json"),
           "REFLECTION_SOURCES": json.dumps([str(f) for f in sources] if sources else None),
           "PYTHONPATH": os.pathsep.join(filter(None, [str(Project.ROOT),
                                                       os.environ.get("PYTHONPATH")]))}
    results = Path(build_dir) / "results.xml"
    results.unlink(missing_ok=True)   # never read a previous run's verdict
    (Path(build_dir) / "coverage.json").unlink(missing_ok=True)
    try:
        runner.test(hdl_toplevel=tb, test_module="Engine.UvmTest", build_dir=build_dir,
                    test_dir=build_dir, extra_env=env, waves=waves, results_xml=results)
    except SystemExit:
        pass        # under pytest the runner exits on failure; the results file says why
    try:
        _, failed = get_results(results)
    except RuntimeError:
        return 1    # simulation died before writing results
    return failed


def regress(module, seeds, params=None, build_dir=None):
    """Run seeds 1..seeds, merge their coverage. Returns (failed seeds, merged coverage)."""
    build_dir = Path(build_dir or Project.ROOT / "sim_build" / module)
    failed, merged = [], None
    for seed in range(1, seeds + 1):
        if run(module, params, seed=seed, build_dir=build_dir):
            failed.append(seed)
        cov = build_dir / "coverage.json"
        if cov.exists():
            data = Coverage.load(cov)
            merged = data if merged is None else Coverage.merge(merged, data)
    if merged is not None:
        Coverage.save(merged, build_dir / "coverage_merged.json")
    return failed, merged


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    module = argv[0]
    params, seed, seeds = {}, None, None
    for arg in argv[1:]:
        k, v = arg.split("=", 1)
        v = int(v) if v.lstrip("-").isdigit() else v
        if k == "seed":
            seed = v
        elif k == "seeds":
            seeds = v
        else:
            params[k] = v
    if seeds is None:
        return run(module, params, seed=seed)
    failed, merged = regress(module, seeds, params)
    print(f"\n{module}: {seeds} seeds, {len(failed)} failed"
          + (f" (seeds {failed}; rerun one with seed=N)" if failed else ""))
    if merged is not None:
        print(Coverage.report(merged))
    return len(failed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
