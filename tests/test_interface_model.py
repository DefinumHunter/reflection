"""End-to-end RTL elaboration to golden cycle-model regression for interfaces."""
import unittest
from pathlib import Path
from types import SimpleNamespace

from Engine.Model import Model


FIXTURE = Path(__file__).resolve().parent / "interface_fixture"


class HandshakeGolden:
    def __init__(self):
        self.cycles = 0

    def tick(self, inputs):
        self.cycles += 1
        return {
            "downstream.data": inputs["upstream.data"],
            "downstream.valid": inputs["upstream.valid"],
            "upstream.ready": inputs["downstream.ready"],
        }


class InterfaceModelTest(unittest.TestCase):
    def test_interface_golden_step(self):
        components = {
            "handshake_stage": SimpleNamespace(
                golden=HandshakeGolden,
                comb={"downstream.data", "downstream.valid", "upstream.ready"},
            ),
        }
        model = Model.from_rtl(
            [FIXTURE / "handshake.sv"], "handshake_single_top", components
        )
        self.assertEqual(len(model.insts), 1)
        self.assertTrue({
            "source_bus.data", "source_bus.valid", "sink_bus.ready"
        }.issubset(model.inputs))
        self.assertTrue({
            "sink_bus.data", "sink_bus.valid", "source_bus.ready"
        }.issubset(model.outputs))

        vectors = [
            (0x1234, 1, 0),
            (0xABCD, 0, 1),
            (0, 1, 1),
        ]
        for data, valid, ready in vectors:
            with self.subTest(data=data, valid=valid, ready=ready):
                result = model.step({
                    "source_bus.data": data,
                    "source_bus.valid": valid,
                    "sink_bus.ready": ready,
                })
                self.assertEqual(result["sink_bus.data"], data)
                self.assertEqual(result["sink_bus.valid"], valid)
                self.assertEqual(result["source_bus.ready"], ready)
        self.assertEqual(model.insts[0].golden.cycles, len(vectors))


if __name__ == "__main__":
    unittest.main()
