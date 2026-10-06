"""The one generic UVM test. Run.py starts it with the module name in the
environment; everything module-specific comes from Project."""
import itertools
import json
import os

import cocotb
import pyuvm
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

import Project
from Engine.Coverage import report, save
from Engine.Uvm import Env, RowSequence


@pyuvm.test()
class ReflectionTest(pyuvm.uvm_test):
    def build_phase(self):
        self.module = os.environ["REFLECTION_MODULE"]
        params = json.loads(os.environ.get("REFLECTION_PARAMS", "{}")) or None
        self.tail = int(os.environ.get("REFLECTION_TAIL", "20"))
        files = json.loads(os.environ.get("REFLECTION_SOURCES", "null"))
        seed = os.environ.get("REFLECTION_SEED")
        self.dut = cocotb.top
        self.model = Project.model(self.module, params=params, files=files)
        self.stimulus = Project.stimulus(self.module, self.model.netlist,
                                         None if seed is None else int(seed))
        self.logger.info(f"{self.module}: seed {self.stimulus.seed}")
        self.coverage = Project.coverage(self.module)
        self.env = Env("env", self, self.dut, self.model, Project.CLOCKS[0],
                       compare=Project.test(self.module).COMPARE, coverage=self.coverage)

    async def run_phase(self):
        self.raise_objection()
        clk = getattr(self.dut, Project.CLOCKS[0])
        Clock(clk, 10, unit="ns").start(start_high=False)
        # after the stimulus: idle rows, so the last transaction is not left
        # standing on the inputs while the pipeline drains
        idle = Project.test(self.module).IDLE
        rows = itertools.chain(self.stimulus, itertools.repeat(dict(idle), self.tail))
        await RowSequence("stimulus", rows).start(self.env.seqr)
        await ClockCycles(clk, 2)                # let the monitors see the last row
        self.drop_objection()

    def extract_phase(self):
        # before check_phase, so the coverage is saved even when the scoreboard fails
        if self.coverage is None:
            return
        self.coverage.sample_ops(self.stimulus.sent)
        data = self.coverage.data()
        self.logger.info("\n" + report(data))
        path = os.environ.get("REFLECTION_COVERAGE")
        if path:
            save(data, path)
