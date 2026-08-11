import importlib.util
import unittest
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).with_name("export_live11_intro.py")


def load_exporter():
    spec = importlib.util.spec_from_file_location("export_live11_intro", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExporterTests(unittest.TestCase):
    def test_arrangement_spec_and_determinism(self):
        ex = load_exporter()
        self.assertEqual((ex.BPM, ex.BARS, ex.BEATS_PER_BAR, ex.SAMPLE_RATE), (164, 64, 4, 48000))
        self.assertEqual(ex.TOTAL_BEATS, 256)
        self.assertEqual(ex.TOTAL_FRAMES, round(256 * 60 / 164 * 48000))
        first = ex.make_event_plan(ex.SEED)
        self.assertEqual(first, ex.make_event_plan(ex.SEED))
        self.assertEqual(set(first), {"Kick", "Snare", "Hats", "Bass", "Metal"})
        self.assertTrue(all(0 <= event[0] < 256 for events in first.values() for event in events))
        self.assertLessEqual({event[2] for event in first["Bass"]}, {39, 40, 41, 43, 45})
        # SC Pbind durations are clock beats: kick dur=1/2 gives 512 slots,
        # with one rest per eight-step amplitude cycle (448 sounding hits).
        self.assertEqual(len(first["Kick"]), 448)
        self.assertEqual(len(first["Snare"]), 128)

    def test_pcm24_encoder_bounds_and_shape(self):
        ex = load_exporter()
        x = np.array([[-1.0, 1.0], [0.0, -0.5]], dtype=np.float32)
        encoded = ex.encode_pcm24(x)
        self.assertIsInstance(encoded, bytes)
        self.assertEqual(len(encoded), x.size * 3)

    def test_voice_positions_are_required_bars(self):
        ex = load_exporter()
        self.assertEqual(ex.VOICE_BARS, (5, 21, 37, 53))
        positions = [ex.bar_to_frame(bar) for bar in ex.VOICE_BARS]
        self.assertEqual(positions, sorted(positions))


if __name__ == "__main__":
    unittest.main()
