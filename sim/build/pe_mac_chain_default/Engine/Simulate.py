"""
Engine/Simulate.py
Phase 4 — generic cocotb entry point. Written once, never touched again.

Dynamically imports Wiring and Stimulus for the active scenario.
SCENARIO_NAME env var drives which test folder is loaded.

Module name is derived from SCENARIO_NAME by stripping the suffix after
the last underscore-separated segment that matches a known module.
"""

import os
import importlib
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

from Paths import RESULTS_DIR
from Engine.Simulation import build_simulation
from Engine.Monitor import run_collector
from Engine.Scoreboard import save, load

CLK_PERIOD_NS   = 10
WATCHDOG_CYCLES = 500

# Map scenario name prefixes to Test package names
MODULE_MAP = {
    "mac_q16":      "MacQ16",
    "pe_input_mux": "PeInputMux",
    "pe_mac_chain": "PeMacChain",
}


def _resolve_module(scenario_name: str) -> str:
    """Derive module key from scenario name. e.g. 'mac_q16_default' → 'mac_q16'"""
    for key in MODULE_MAP:
        if scenario_name.startswith(key):
            return key
    raise ValueError(f"Cannot resolve module from scenario name: {scenario_name!r}")


@cocotb.test()
async def test_generic(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    # Resolve which module this scenario belongs to
    name        = os.environ.get("SCENARIO_NAME", "")
    module_key  = _resolve_module(name)
    package     = MODULE_MAP[module_key]

    # Dynamic imports — equivalent to the static imports in old Simulate.py files
    wiring_mod  = importlib.import_module(f"Tests.{package}.Wiring")
    stimulus_mod = importlib.import_module(f"Tests.{package}.Stimulus")

    nodes   = wiring_mod.nodes
    edges   = wiring_mod.edges
    dut_map = {key: dut for key in wiring_mod.dut_keys}

    if not name:
        name = stimulus_mod.DEFAULT.name

    # Load precomputed stream
    stream = load(RESULTS_DIR / f"{name}_stream.csv")

    sim    = build_simulation(nodes, edges, dut_map)
    actual = []

    sim.start()

    async def _generator():
        for cycle in stream:
            await sim.input_queue.put(cycle)
        await sim.input_queue.put(None)
        cocotb.log.info(f"[{name}] generator done — {len(stream)} cycles")

    col_task = cocotb.start_soon(
        run_collector(sim.output_queue, actual, len(stream))
    )
    cocotb.start_soon(_generator())

    async def watchdog():
        await ClockCycles(dut.clk, WATCHDOG_CYCLES)
        if not sim._stop_event.is_set():
            dut._log.warning("[watchdog] forcing stop")
            sim.stop()

    cocotb.start_soon(watchdog())

    await col_task
    sim.stop()

    save(RESULTS_DIR / f"{name}_actual.csv", actual)
    cocotb.log.info(f"[{name}] saved {len(actual)} cycles")