# Reflection — Roadmap

Known gaps and planned improvements, in priority order.

---

## 1. SVA integration

SVA checkers exist alongside the RTL (`tb/sva/`) but are not wired into the
five-phase flow. Currently they compile but their assertions are not collected,
reported, or surfaced through the scoreboard.

**Goal:** Stage 4 should compile SVA checker files together with the DUT and
testbench, and Stage 5 should include assertion pass/fail counts in the
scoreboard summary. A test should be able to fail on SVA violations alone,
without any scoreboard mismatch.

**Why it matters:** SVA covers properties that are difficult to express as
input/output comparisons — protocol ordering, forbidden state transitions,
timing invariants. Without SVA integration, Reflection only verifies functional
correctness at the output boundary.

---

## 2. Internal signal extraction

Currently `RTLParams.py` reads parameters (e.g. `PIPELINE_STAGES`) from the
testbench file. Signal specifications — input names, output names, bit widths —
must be written manually in `Wiring.py` and `Components/`.

**Goal:** Given an RTL source file, Reflection should be able to extract port
declarations automatically and produce a signal spec without manual entry. This
is the primary enabler for the intended AI-assisted workflow: an AI reads the
RTL and the framework documentation, then generates the test data files with
minimal chance of error.

**Why it matters:** Manual signal specs are the biggest friction point when
adding a new module. Automating extraction removes the step most likely to
introduce mistakes and makes Reflection genuinely reusable across arbitrary RTL.

---

## 3. Clock-relative sampling

The monitor currently samples outputs on a fixed implicit clock edge.
For modules where valid data appears at a specific phase relationship to the
clock — for example, UART, SPI, or any protocol with setup/hold constraints —
this is insufficient.

**Goal:** `Wiring.py` or `TestConfig.py` should be able to specify which clock
signal drives sampling and on which edge relative to that clock outputs are
captured.

---

## 4. Stimulus and filter elaboration

`VectorConfig` and `CheckConfig` are minimal. The full set of useful options
for stimulus generation (burst patterns, protocol-aware sequences, constrained
random) and output filtering (window-based checks, per-signal tolerances for
fixed-point rounding) is not yet known.

**Goal:** Expand these APIs as real verification needs surface during use.
No specific changes are planned — gaps will become clear as more modules are
verified.
