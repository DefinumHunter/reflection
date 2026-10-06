"""
Engine/Node.py
Generic node lifecycle. Written once, never touched again.

NodeInstance receives the DUT handle directly from build_simulation().
If a node has no accessible input signals on the DUT (e.g. intermediate
nodes in a wrapped chain), it skips reset driving and waits instead.
"""

import cocotb
from cocotb.triggers import RisingEdge
from cocotb.queue import Queue

from Engine.Driver  import run_driver
from Engine.Monitor import run_monitor


class NodeInstance:

    def __init__(self, nodedef, dut, input_queue: Queue, output_queues: list):
        self._nodedef      = nodedef
        self._dut          = dut
        self.input_queue   = input_queue
        self.output_queues = output_queues
        self._stop_event   = cocotb.triggers.Event()
        self._done_driving = cocotb.triggers.Event()

    def start(self):
        #cocotb.log.info(f"[{nd.name}] reset done, starting driver+monitor")
        cocotb.start_soon(self._reset_and_run())

    def stop(self):
        self._stop_event.set()

    async def wait_done(self):
        await self._stop_event.wait()

    async def _reset_and_run(self):
        dut = self._dut
        nd  = self._nodedef

        # Check if this node has any signals it can actually drive on the DUT.
        # If not (e.g. mac in a wrapped chain where inputs are internal),
        # skip reset driving and just wait for the other node's reset to finish.
        has_inputs = any(
            getattr(dut, name, None) is not None
            for name in nd.input_signals
        )

        if has_inputs:
            # This node owns the reset sequence
            if hasattr(dut, "rst_n"):
                dut.rst_n.value = 0
            for name in nd.input_signals:
                if name != "rst_n":
                    sig = getattr(dut, name, None)
                    if sig is not None:
                        sig.value = 0

            for _ in range(nd.reset_cycles):
                await RisingEdge(dut.clk)

            if hasattr(dut, "rst_n"):
                dut.rst_n.value = 1
            await RisingEdge(dut.clk)
        else:
            # This node has no top-level inputs — wait for reset to complete
            for _ in range(nd.reset_cycles + 1):
                await RisingEdge(dut.clk)

        cocotb.start_soon(run_driver(
            dut         = dut,
            signal_spec = nd.input_signals,
            input_queue = self.input_queue,
            done_event  = self._done_driving,
            stop_event  = self._stop_event,
        ))
        cocotb.start_soon(run_monitor(
            dut            = dut,
            output_signals = nd.output_signals,
            output_queues  = self.output_queues,
            stop_event     = self._stop_event,
        ))