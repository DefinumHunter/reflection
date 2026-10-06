"""
Engine/ArchBase.py
Core datastructures and builder. Written once, never touched again.

Stage 1: build_reference(nodes, edges) → ChainReference
Stage 4: build_simulation(nodes, edges, duts) → SimHandle
"""

from collections import deque
from dataclasses import dataclass, field


# ── NodeDef ───────────────────────────────────────────────────────

@dataclass
class NodeDef:
    """
    One RTL module instance in the architecture graph.

    name           — unique identifier used in edge strings
    input_signals  — { port_name: SignalSpec } driver uses this
    output_signals — { port_name: SignalSpec } monitor uses this
    golden         — callable: dict → dict (full cycle, handles in_vld=0)
    pipeline_depth — number of pipeline stages, read from RTL params
    reset_cycles   — how many cycles to hold rst_n low
    """
    name:           str
    input_signals:  dict
    output_signals: dict
    golden:         object
    pipeline_depth: int
    reset_cycles:   int  = 5
    config:         dict = field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────

def _translate(sample: dict, signal_map: dict) -> dict:
    """Rename keys per signal_map. Unmentioned keys pass through."""
    if not signal_map:
        return sample.copy()
    return {signal_map.get(k, k): v for k, v in sample.items()}


def _zero_output(node: NodeDef) -> dict:
    """All-zero dict matching node's output signals."""
    return {name: 0 for name in node.output_signals}


def _parse_edges(edges: list) -> list:
    """Normalize edges to (src, dst, signal_map) tuples."""
    result = []
    for edge in edges:
        if len(edge) == 2:
            result.append((edge[0], edge[1], {}))
        else:
            result.append((edge[0], edge[1], edge[2]))
    return result


def _ordered_nodes(nodes: list, edges: list) -> list:
    """
    Walk edges from generator to collector.
    Returns ordered list of (NodeDef, signal_map).
    signal_map is the map on the edge LEAVING this node —
    it translates this node's output names to the next node's input names.
    Linear chains only.
    """
    node_map   = {nd.name: nd for nd in nodes}
    parsed     = _parse_edges(edges)
    edge_index = {src: (dst, smap) for src, dst, smap in parsed}

    ordered = []
    current = "generator"

    while True:
        if current not in edge_index:
            break
        dst, smap = edge_index[current]
        if dst == "collector":
            break
        nd = node_map[dst]
        # smap is the map on the edge that brought us TO this node
        # we need the map on the edge LEAVING this node
        leaving_dst, leaving_map = edge_index.get(dst, (None, {}))
        ordered.append((nd, leaving_map))
        current = dst

    return ordered


# ── ChainReference ────────────────────────────────────────────────

class ChainReference:
    """
    Stateful callable — models the complete circuit one cycle at a time.
    Read before push — matches hardware register behavior.
    First sum(depths) outputs are zeros — matching hardware pipeline fill.
    """

    def __init__(self, stages: list):
        # stages: list of (NodeDef, signal_map_in)
        self._stages = stages
        self._pipes  = [
            deque(
                [_zero_output(nd) for _ in range(nd.pipeline_depth)],
                maxlen=nd.pipeline_depth
            )
            for nd, _ in stages
        ]

    def __call__(self, inp: dict) -> dict:
        current = inp
        for i, (nd, map_in) in enumerate(self._stages):
            # translate input names if needed
            translated = _translate(current, map_in)
            # read delayed output BEFORE pushing (matches hardware)
            delayed = self._pipes[i][-1].copy()
            # compute golden for this cycle
            result = nd.golden(translated)
            # push result into shift register
            self._pipes[i].appendleft(result)
            # pass delayed output to next stage
            current = delayed
        return current

    @property
    def total_depth(self) -> int:
        return sum(nd.pipeline_depth for nd, _ in self._stages)


# ── Stage 1: build_reference ──────────────────────────────────────

def build_reference(nodes: list, edges: list) -> ChainReference:
    """
    Stage 1 — build the reference function.
    Pure Python, no DUT, no cocotb.
    """
    stages = _ordered_nodes(nodes, edges)
    return ChainReference(stages)


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
    Returned by build_simulation().
    Everything Simulate.py needs — no module-specific knowledge required.
    """

    def __init__(self, input_queue, output_queue,
                 done_driving, stop_fn, total_depth,
                 start_fn):
        self.input_queue  = input_queue   # generator pushes here
        self.output_queue = output_queue  # collector reads here
        self.done_driving = done_driving  # Event: fires when driver done
        self.total_depth  = total_depth   # sum of all pipeline depths
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
    Creates queues, delay coroutines, translator coroutines.

    duts: { node_name: cocotb_dut_handle }
    For standalone: duts = {"mac": dut}
    For wrapper:    duts = {"mux": dut, "mac": dut}  (wrapper exposes all signals)
    For hierarchy:  duts = {"mux": dut.u_mux, "mac": dut.u_mac}
    """
    import cocotb
    from cocotb.queue import Queue
    from Engine.Node import NodeInstance

    stages     = _ordered_nodes(nodes, edges)
    stop_event = cocotb.triggers.Event()
    done_event = cocotb.triggers.Event()

    input_queue  = Queue()
    output_queue = Queue()

    prev_queue = input_queue
    instances  = {}
    coroutines = []   # (fn, *args) to start when start() is called

    for i, (nd, map_in) in enumerate(stages):
        dut     = duts[nd.name]
        is_last = (i == len(stages) - 1)

        # monitor pushes to raw_out
        raw_out = Queue()

        # delay queue sits between raw_out and the next stage
        if is_last:
            after_delay = output_queue
        else:
            after_delay = Queue()

        instance = NodeInstance(
            nodedef       = nd,
            input_queue   = prev_queue,
            output_queues = [raw_out],
        )
        # all nodes share one stop_event
        instance._stop_event = stop_event

        # only the last node's done_driving matters
        if is_last:
            instance._done_driving = done_event

        instances[nd.name] = instance

        # delay queue coroutine
        coroutines.append(
            (_delay_queue, raw_out, after_delay,
             nd.pipeline_depth, _zero_output(nd))
        )

        # translator coroutine — only needed between nodes, not at output
        if not is_last and map_in:
            translated_q = Queue()
            coroutines.append(
                (_translator, after_delay, translated_q, map_in)
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
        total_depth  = sum(nd.pipeline_depth for nd, _ in stages),
        start_fn     = _start,
    )