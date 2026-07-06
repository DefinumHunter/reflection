# Reflection

A five-phase RTL verification framework built on [cocotb](https://www.cocotb.org/).  
Inspired by UVM's separation of concerns — without class inheritance.

Reflection builds a Python mirror of an RTL module's datapath, runs it ahead of
simulation to produce expected outputs, then compares those outputs against the
real RTL after simulation completes. Each phase is isolated: pure Python stages
run before cocotb starts, and the simulation stage only drives and collects signals.

A real-world usage example can be found in
[transform-accelerator](https://github.com/DefinumHunter/transform-accelerator).

---

## The five phases

| Phase | What happens |
|-------|-------------|
| 1 — Build reference | Construct a Python graph of the RTL topology from `Wiring.py` |
| 2 — Generate stream | Produce input stimulus vectors from `Stimulus.py` and save to CSV |
| 3 — Run reference | Feed the stream through the golden model and save expected outputs to CSV |
| 4 — Simulate | Compile RTL, run cocotb, drive the same stream into the DUT, collect actual outputs |
| 5 — Scoreboard | Compare expected vs actual CSVs and report pass/fail |

Phases 1–3 and 5 are pure Python. Phase 4 is the only phase that touches cocotb.

---

## Repository structure

```
reflection/
├── run.py                  # Single entry point — runs all five phases
├── config.py               # Simulator configuration (Icarus, Questa, VCS, Xcelium)
├── ROADMAP.md              # Known gaps and planned improvements
└── sim/
    ├── Engine/             # Generic machinery — never modified for a new module
    │   ├── ArchBase.py     # Graph builder and reference model runner
    │   ├── Driver.py       # Cocotb signal driver
    │   ├── Generators.py   # Stimulus stream generator
    │   ├── Monitor.py      # Cocotb output collector
    │   ├── Node.py         # NodeInstance — wraps driver and monitor
    │   ├── RTLParams.py    # Reads parameters from testbench files
    │   ├── Scoreboard.py   # CSV save/load/compare
    │   ├── Simulate.py     # Generic cocotb entry point
    │   ├── Simulation.py   # SimHandle builder
    │   └── TestScenario.py # TestScenario and StimulusConfig dataclasses
    ├── Components/         # Module-specific signal specs and golden models
    │   └── __init__.py     # Populate for your module — see transform-accelerator
    └── Tests/              # One subfolder per module under test
        └── __init__.py     # Populate for your module — see transform-accelerator
```

---

## Adding a new module

Create one subfolder under `sim/Tests/` with four pure-data files:

| File | What it contains |
|------|-----------------|
| `Wiring.py` | `nodes`, `edges`, `dut_keys` — RTL topology and signal specs |
| `Stimulus.py` | `StimulusConfig` — input vectors and generation parameters |
| `Checks.py` | `CheckConfig` — which signals to compare and how to filter |
| `Build.py` | `TEST_PLAN` — list of `TestScenario` instances to run |

Add a `Components/` entry with the module's input/output signal specs and golden
model cycle function. Then run:

```
python run.py --module your_module_name
```

No changes to `Engine/` are required.

---

## Running tests

```
# Run a single module
python run.py --module mac_q16

# Run all modules
python run.py --module all

# Run with waveform dump
python run.py --module mac_q16 --waves

# Select simulator
python run.py --module mac_q16 --sim xcelium
```

Supported simulators are configured in `config.py`: `icarus` (default), `questa`,
`vcs`, `xcelium`.

---

## Design principles

**Composition over inheritance.** There are no base classes to extend. A new module
is a set of data files — signal names, vectors, a golden function, a check config.

**Pure data for test configuration.** Files in `Tests/<Module>/` contain no control
flow. All execution logic lives in `Engine/`.

**Precomputed expected outputs.** The golden model runs before simulation starts.
The scoreboard compares two CSV files — no in-simulation reference computation.

**Engine is frozen.** Once `Engine/` is working, it is never modified. Adding a new
module only adds files to `Tests/` and `Components/`.

---

## Requirements

- Python 3.10+
- [cocotb](https://docs.cocotb.org/en/stable/install.html) 2.0+
- A supported simulator: Icarus Verilog, Questa, Synopsys VCS, or Cadence Xcelium
