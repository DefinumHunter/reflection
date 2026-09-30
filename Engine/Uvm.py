"""Generic pyuvm components. Written once, used for every module.

Nothing here knows about a particular DUT: the signal lists come from the
parsed TB (the same netlist the model is built from), the stimulus comes from
Modules/<module>/Test.py through Engine/Generator.py.

Timing (the same convention as Model.step() and tests/icarus.py):
    Driver      writes row c right after the rising edge that starts cycle c.
    Monitors    sample on the falling edge inside cycle c, i.e. what the
                flops will see at the next rising edge, and what the outputs
                are during cycle c. One extra sample is taken before the first
                edge (power-up), so the model also ticks on it, as the RTL does.
    Predictor   feeds each sampled input row to Model.step() -> expected row c.
    Scoreboard  compares expected row c with sampled output row c.
"""
import cocotb
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge, Timer
from cocotb.types import LogicArray
from Engine.Checks import exact
from pyuvm import (uvm_analysis_port, uvm_component, uvm_driver, uvm_env, uvm_get_port,
                   uvm_sequence, uvm_sequence_item, uvm_sequencer, uvm_subscriber,
                   uvm_tlm_analysis_fifo)


def read(handle):
    """Signal value as an unsigned int, or None if it has any X/Z bit."""
    v = handle.value
    if not v.is_resolvable:
        return None
    return v.to_unsigned() if hasattr(v, "to_unsigned") else int(v)


def write(handle, value):
    handle.value = LogicArray("X" * len(handle)) if value is None else value


# --- stimulus ---------------------------------------------------------------

class Row(uvm_sequence_item):
    """One cycle of stimulus: {TB input: value}. Inputs not in the row keep
    their previous value."""

    def __init__(self, name, values):
        super().__init__(name)
        self.values = values

    def __str__(self):
        return str(self.values)


class RowSequence(uvm_sequence):
    """Wraps a plain Python iterable of rows (dicts) into a UVM sequence."""

    def __init__(self, name, rows):
        super().__init__(name)
        self.rows = rows

    async def body(self):
        for i, values in enumerate(self.rows):
            item = Row(f"row{i}", values)
            await self.start_item(item)
            await self.finish_item(item)


class Driver(uvm_driver):
    def __init__(self, name, parent, clk, signals):
        super().__init__(name, parent)
        self.clk, self.signals = clk, signals

    async def run_phase(self):
        while True:
            item = await self.seq_item_port.get_next_item()
            await RisingEdge(self.clk)
            for name, value in item.values.items():
                if name not in self.signals:
                    raise KeyError(f"stimulus sets '{name}', which is not a TB input; "
                                   f"inputs: {sorted(self.signals)}")
                write(self.signals[name], value)
            self.seq_item_port.item_done()


# --- observation -----------------------------------------------------------

class Monitor(uvm_component):
    """Samples a set of TB signals once per cycle and publishes {name: value}."""

    def __init__(self, name, parent, clk, signals):
        super().__init__(name, parent)
        self.clk, self.signals = clk, signals
        self.ap = uvm_analysis_port("ap", self)

    def sample(self):
        return {n: read(h) for n, h in self.signals.items()}

    async def run_phase(self):
        await Timer(1, "ns")                 # power-up state, before the first edge
        self.ap.write(self.sample())
        while True:
            await FallingEdge(self.clk)
            await ReadOnly()
            self.ap.write(self.sample())


class Predictor(uvm_subscriber):
    """Sampled inputs -> Model.step() -> expected outputs."""

    def __init__(self, name, parent, model):
        super().__init__(name, parent)
        self.model = model
        self.ap = uvm_analysis_port("ap", self)

    def write(self, inputs):
        self.ap.write(self.model.step(inputs))


class Scoreboard(uvm_component):
    """Compares expected and actual outputs cycle by cycle with a compare rule
    from Engine/Checks.py (default: exact, skipping values the model says are X).
    Fails the test in check_phase if there is any mismatch or if nothing was
    compared at all.
    """

    def __init__(self, name, parent, compare=exact, show=10):
        super().__init__(name, parent)
        self.compare_rule, self.show = compare, show

    def build_phase(self):
        self.exp_fifo = uvm_tlm_analysis_fifo("exp_fifo", self)
        self.act_fifo = uvm_tlm_analysis_fifo("act_fifo", self)
        self.exp_get = uvm_get_port("exp_get", self)
        self.act_get = uvm_get_port("act_get", self)
        self.exp_export = self.exp_fifo.analysis_export
        self.act_export = self.act_fifo.analysis_export

    def connect_phase(self):
        self.exp_get.connect(self.exp_fifo.get_export)
        self.act_get.connect(self.act_fifo.get_export)

    def compare(self):
        self.cycles = self.compared = self.skipped = 0
        self.mismatches = []
        while self.exp_get.can_get() and self.act_get.can_get():
            _, exp = self.exp_get.try_get()
            _, act = self.act_get.try_get()
            bad = self.compare_rule(exp, act)
            known = sum(e is not None for e in exp.values())
            self.skipped += len(exp) - known
            self.compared += known - len(bad)
            self.mismatches += [(self.cycles, s, e, a) for s, e, a in bad]
            self.cycles += 1

    def check_phase(self):
        self.compare()
        fmt = lambda v: "X" if v is None else f"0x{v:x}"
        self.logger.info(f"{self.cycles} cycles, {self.compared} values matched, "
                         f"{self.skipped} skipped (model X), {len(self.mismatches)} mismatches")
        for c, sig, e, a in self.mismatches[:self.show]:
            self.logger.error(f"cycle {c}: {sig} expected {fmt(e)}, got {fmt(a)}")
        if len(self.mismatches) > self.show:
            self.logger.error(f"... and {len(self.mismatches) - self.show} more")
        assert self.compared > 0, "scoreboard compared nothing"
        assert not self.mismatches, f"{len(self.mismatches)} mismatches"


# --- assembly ---------------------------------------------------------------

class Env(uvm_env):
    """dut, model and the signal lists are passed in by the test."""

    def __init__(self, name, parent, dut, model, clock="clk", compare=exact):
        super().__init__(name, parent)
        self.dut, self.model, self.clock, self.compare = dut, model, clock, compare

    def build_phase(self):
        clk = getattr(self.dut, self.clock)
        handles = lambda names: {n: getattr(self.dut, n) for n in names}
        self.seqr = uvm_sequencer("seqr", self)
        self.driver = Driver("driver", self, clk, handles(self.model.inputs))
        self.in_mon = Monitor("in_mon", self, clk, handles(self.model.inputs))
        self.out_mon = Monitor("out_mon", self, clk, handles(self.model.outputs))
        self.predictor = Predictor("predictor", self, self.model)
        self.scoreboard = Scoreboard("scoreboard", self, self.compare)

    def connect_phase(self):
        self.driver.seq_item_port.connect(self.seqr.seq_item_export)
        self.in_mon.ap.connect(self.predictor.analysis_export)
        self.predictor.ap.connect(self.scoreboard.exp_export)
        self.out_mon.ap.connect(self.scoreboard.act_export)
