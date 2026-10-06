"""
Engine/Monitor.py
Generic cocotb monitor. Written once, never touched again.
"""

from cocotb.triggers import RisingEdge


async def run_monitor(dut, output_signals: dict, output_queues: list, stop_event):
    while not stop_event.is_set():
        await RisingEdge(dut.clk)

        sample = {}
        for name, spec in output_signals.items():
            sig = getattr(dut, name, None)
            if sig is None:
                continue
            val = int(sig.value) & spec.width_mask
            sample[name] = val

        for q in output_queues:
            q.put_nowait(sample)


async def run_collector(output_queue, stream: list, max_samples: int):
    """
    Drains output_queue into stream until max_samples collected.
    Count-based exit guarantees actual length matches stream length exactly.
    """
    while len(stream) < max_samples:
        sample = await output_queue.get()
        stream.append(sample)
        if len(stream) % 20 == 0:
            import cocotb
            cocotb.log.info(f"[collector] got {len(stream)}/{max_samples}")