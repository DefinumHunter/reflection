"""Build and run the UVM test for one module in Icarus, no make needed.

    python -m Engine.Run pe_mac_wrapper
    python -m Engine.Run mac_q16 PIPELINE_STAGES=6
    python -m Engine.Run pe_mac_wrapper seed=1234     (reproduce a failing run)

Returns / exits with the number of failed tests (0 = pass).
"""
import json
import os
import sys
from pathlib import Path

from cocotb_tools.runner import get_results, get_runner

import Project


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
           "REFLECTION_SOURCES": json.dumps([str(f) for f in sources] if sources else None),
           "PYTHONPATH": os.pathsep.join(filter(None, [str(Project.ROOT),
                                                       os.environ.get("PYTHONPATH")]))}
    results = Path(build_dir) / "results.xml"
    results.unlink(missing_ok=True)   # never read a previous run's verdict
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


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    module = argv[0]
    params, seed = {}, None
    for arg in argv[1:]:
        k, v = arg.split("=", 1)
        v = int(v) if v.lstrip("-").isdigit() else v
        if k == "seed":
            seed = v
        else:
            params[k] = v
    return run(module, params, seed=seed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
