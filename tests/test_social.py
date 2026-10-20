import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from mcstats.config import Config
from mcstats.hall import hall_of_fame
from mcstats.history import History
from mcstats.recap import recap
from mcstats.social import buddies, pvp
from mcstats.world import world_state


class BuddiesTest(unittest.TestCase):
    def test_overlap(self):
        sessions = [("Steve", "2026-01-01 10:00:00", "2026-01-01 12:00:00"),
                    ("Alex", "2026-01-01 11:00:00", "2026-01-01 13:00:00"),
                    ("Kai", "2026-01-01 14:00:00", "2026-01-01 15:00:00")]
        self.assertEqual(buddies(sessions), [{"a": "Alex", "b": "Steve", "s": 3600}])  # Kai never overlaps

    def test_still_online(self):
        now = dt.datetime(2026, 1, 1, 12, 30)
        sessions = [("Steve", "2026-01-01 12:00:00", None), ("Alex", "2026-01-01 12:10:00", None)]
        self.assertEqual(buddies(sessions, now)[0]["s"], 20 * 60)


class PvpTest(unittest.TestCase):
    def test_only_player_killers(self):
        profiles = {"Steve": {"deaths": [{"m": "was slain by Alex"}, {"m": "was slain by Zombie"}, {"m": "was shot by Alex using [Bow]"}]},
                    "Alex": {"deaths": []}}
        self.assertEqual(pvp(profiles), [{"killer": "Alex", "victim": "Steve", "n": 2}])


class HallTest(unittest.TestCase):
    def test_first_wins(self):
        adv = {"Steve": {"story/mine_diamond": "2026-01-02 10:00:00"}, "Alex": {"story/mine_diamond": "2026-01-01 09:00:00"}}
        profiles = {"Steve": {"first": "2026-01-01 08:00:00", "deaths": []}, "Alex": {"first": "2026-01-01 08:30:00", "deaths": []}}
        hall = {h["key"]: h for h in hall_of_fame(adv, profiles)}
        self.assertEqual(hall["first_diamond"]["p"], "Alex")
        self.assertEqual(hall["first_diamond"]["n"], 2)
        self.assertEqual(hall["first_join"]["p"], "Steve")


class HistoryTest(unittest.TestCase):
    def test_week_change_and_recap(self):
        with tempfile.TemporaryDirectory() as d:
            h = History(Config(data_dir=Path(d)))
            old = dt.date.today() - dt.timedelta(days=8)
            h.record({"Steve": {"xp": 100, "playtime": 0}, "Alex": {"xp": 100, "playtime": 0}}, day=old)
            report = h.report({"Steve": {"xp": 400, "playtime": 3600, "blocks_mined": 50, "mob_kills": 3},
                               "Alex": {"xp": 150, "playtime": 60}})
            self.assertEqual(report["week"]["since"], old.isoformat())
            self.assertEqual(report["week"]["players"]["Steve"]["xp"], 300)
            message = json.loads(recap({"history": report}, "en", "http://example.org"))
            self.assertEqual(message[1]["text"].strip(), "Steve")
            self.assertEqual(message[-1]["click_event"]["url"], "http://example.org")

    def test_no_recap_without_history(self):
        with tempfile.TemporaryDirectory() as d:
            report = History(Config(data_dir=Path(d))).report({"Steve": {"xp": 400}})
            self.assertIsNone(recap({"history": report}, "en"))


class WorldTest(unittest.TestCase):
    def test_missing_files_give_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            w = world_state(Config(minecraft_dir=Path(d)))
            self.assertEqual(w["day"], 1)
            self.assertFalse(w["raining"])
            self.assertIsNone(w["time_of_day"])


if __name__ == "__main__":
    unittest.main()
