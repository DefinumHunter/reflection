"""
Engine/Driver.py
Generic cocotb driver. Written once, never touched again.

Reads complete cycle dicts from input_queue, drives all signals
on the DUT by name. Drives on FallingEdge so RTL latches on the
next RisingEdge with full setup time margin.

Signals not present on the DUT are silently skipped — this allows
the same driver to work for both standalone tests and wrapped chain
tests where some signals are driven internally by the RTL.
"""

import cocotb
from cocotb.triggers import FallingEdge


async def run_driver(dut, signal_spec: dict, input_queue, done_event, stop_event):
    """
    dut          — cocotb DUT handle
    signal_spec  — dict of { signal_name: SignalSpec }
    input_queue  — Queue of cycle dicts | None sentinel
    done_event   — set when sentinel is seen
    stop_event   — set externally to force stop
    """
    while not stop_event.is_set():
        cycle = await input_queue.get()

        if cycle is None:
            cocotb.log.debug("[driver] sentinel — done driving")
            done_event.set()
            return

        await FallingEdge(dut.clk)

        for name, spec in signal_spec.items():
            sig = getattr(dut, name, None)
            if sig is None:
                continue   # signal not at this DUT level — skip silently

            val = cycle.get(name, 0)
            val &= spec.width_mask
            if spec.signed and val >= spec.sign_threshold:
                val -= (1 << spec.width)
            sig.value = val