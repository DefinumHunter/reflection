"""
Engine/Simulation.py
Stage 4 — simulation handle. Cocotb-dependent.
Written once, never touched again.

build_simulation(nodes, edges, duts) → SimHandle

Separate from ArchBase.py because:
  - ArchBase is pure Python, runs before cocotb starts
  - Simulation requires cocotb context (Queue, Event, coroutines)
"""

import cocotb
from cocotb.queue import Queue

from Engine.ArchBase import NodeDef, _ordered_nodes, _translate, _zero_output
from Engine.Node import NodeInstance


# ── Delay queue coroutine ─────────────────────────────────────────

async def _delay_queue(src_queue, dst_queue, depth: int, zero: dict):
    """
    Inserts pipeline_depth zero samples before passing real data.
    Sits between monitor output and next stage's input.
    Passes None sentinel through to signal end of stream.
    """
    for _ in range(depth):
        await dst_queue.put(zero.copy())
    while True:
        item = await src_queue.get()
        await dst_queue.put(item)
        if item is None:
            return


# ── Translator coroutine ──────────────────────────────────────────

async def _translator(src_queue, dst_queue, signal_map: dict):
    """
    Translates signal names between two connected nodes.
    Sits between one node's delayed output and the next node's input.
    Passes None sentinel through.
    """
    while True:
        item = await src_queue.get()
        if item is None:
            await dst_queue.put(None)
            return
        await dst_queue.put(_translate(item, signal_map))


# ── SimHandle ─────────────────────────────────────────────────────

class SimHandle:
    """
    Everything Simulate.py needs — no module-specific knowledge required.

    input_queue   — generator pushes stream cycles here
    output_queue  — collector reads actual samples from here
    done_driving  — Event: fires when the last driver sees the sentinel
    total_depth   — sum of all pipeline depths in the chain
    start()       — launch all nodes, delay queues, translators
    stop()        — signal all coroutines to finish
    """

    def __init__(self, input_queue, output_queue,
                 done_driving, stop_fn, start_fn, total_depth,
                 stop_event):
        self.input_queue  = input_queue
        self.output_queue = output_queue
        self.done_driving = done_driving
        self.total_depth  = total_depth
        self._stop_event  = stop_event   # for run_collector compatibility
        self._stop_fn     = stop_fn
        self._start_fn    = start_fn

    def start(self):
        """Launch all nodes, delay queues, and translators."""
        self._start_fn()

    def stop(self):
        """Signal all coroutines to finish."""
        self._stop_fn()


# ── Stage 4: build_simulation ─────────────────────────────────────

def build_simulation(nodes: list, edges: list, duts: dict) -> SimHandle:
    """
    Stage 4 — build the simulation handle.

    duts: { node_name: cocotb_dut_handle }

    For standalone test:
        duts = {"mac": dut}

    For wrapper (all signals at top level):
        duts = {"mux": dut, "mac": dut}

    For hierarchical DUT:
        duts = {"mux": dut.u_mux, "mac": dut.u_mac}

    Returns SimHandle with input_queue, output_queue, done_driving,
    start(), stop().
    """
    stages     = _ordered_nodes(nodes, edges)
    stop_event = cocotb.triggers.Event()
    done_event = cocotb.triggers.Event()

    input_queue  = Queue()
    output_queue = Queue()

    prev_queue = input_queue
    instances  = {}
    coroutines = []   # list of (coroutine_fn, *args) — started in start()

    for i, (nd, map_out) in enumerate(stages):
        dut     = duts[nd.name]
        is_last = (i == len(stages) - 1)

        # monitor pushes raw samples here
        raw_out = Queue()

        if is_last:
            # last node — monitor output goes directly to collector
            # no delay queue needed here, RTL timing is what it is
            instance = NodeInstance(
                nodedef       = nd,
                dut           = dut,
                input_queue   = prev_queue,
                output_queues = [output_queue],
            )
            instance._stop_event = stop_event
            instance._done_driving = done_event
            instances[nd.name] = instance
            # no delay coroutine for last node
        else:
            # intermediate node — delay queue + translator to next node
            after_delay = Queue()

            instance = NodeInstance(
                nodedef       = nd,
                dut           = dut,
                input_queue   = prev_queue,
                output_queues = [raw_out],
            )
            instance._stop_event = stop_event
            instances[nd.name] = instance

            # delay coroutine: raw_out → after_delay
            coroutines.append(
                (_delay_queue, raw_out, after_delay,
                 nd.pipeline_depth, _zero_output(nd))
            )

            if map_out:
                translated_q = Queue()
                coroutines.append(
                    (_translator, after_delay, translated_q, map_out)
                )
                prev_queue = translated_q
            else:
                prev_queue = after_delay

    def _start():
        for instance in instances.values():
            instance.start()
        for fn, *args in coroutines:
            cocotb.start_soon(fn(*args))

    def _stop():
        stop_event.set()

    return SimHandle(
        input_queue  = input_queue,
        output_queue = output_queue,
        done_driving = done_event,
        stop_fn      = _stop,
        start_fn     = _start,
        total_depth  = sum(nd.pipeline_depth for nd, _ in stages),
        stop_event   = stop_event,
    )