import tempfile
import unittest
from pathlib import Path

from mcstats.config import Config
from mcstats.milestones import Milestones, level, next_round


def fun(diamonds):
    return {"rows": [{"key": "diamond_ore", "values": {"Steve": diamonds * 0.75, "Alex": diamonds * 0.25}}]}


class MilestoneTest(unittest.TestCase):
    def test_round_numbers(self):
        self.assertEqual([next_round(n) for n in (100, 200, 500, 1000)], [200, 500, 1000, 2000])
        self.assertEqual(level(99, 100), 0)
        self.assertEqual(level(562, 100), 500)
        self.assertEqual(level(1000, 100), 1000)

    def test_first_run_is_quiet_then_new_ones_are_announced(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(data_dir=Path(d))
            said = []
            m = Milestones(cfg)
            m.announce = said.extend
            m.check(fun(562), {}, {"Steve"})
            self.assertEqual(said, [])
            m = Milestones(cfg)  # reads what the first run wrote
            m.announce = said.extend
            m.check(fun(600), {}, {"Steve"})
            self.assertEqual(said, [])
            m.check(fun(2100), {}, {"Steve"})  # 1000 and 2000 at once: only the highest
            import time; time.sleep(0.1)
            self.assertEqual([(e["key"], e["n"], e["top"]) for e in said], [("diamond_ore", 2000, "Steve")])
            self.assertEqual(m.report(fun(2100), {})["log"][0]["n"], 2000)
