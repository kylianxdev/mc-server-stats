import json
import tempfile
import unittest
from pathlib import Path

from mcstats.config import Config
from mcstats.logs import LogParser

LOG = """\
[10:00:00] [Server thread/INFO]: Steve[/203.0.113.7:51234] logged in with entity id 1 at ([world]0.0, 64.0, 0.0)
[10:00:00] [Server thread/INFO]: System chat: Steve joined the game
[10:01:00] [Server thread/INFO]: Steve issued server command: /msg Alex secret meeting at my base
[10:02:00] [Server thread/INFO]: Steve issued server command: /tp -277 ~ -229
[10:03:00] [Server thread/INFO]: System chat: Made Steve a server operator
[10:04:00] [Server thread/INFO]: Steve issued server command: /gamemode creative
[10:05:00] [Server thread/INFO]: System chat: Steve has made the advancement [Diamonds!]
[10:06:00] [Server thread/INFO]: System chat: Steve was slain by Zombie
[10:06:30] [Server thread/INFO]: System chat: Steve has the following entity data: {id: "minecraft:diamond_chestplate"}
[10:07:00] [Server thread/INFO]: System chat: Added Alex to the whitelist
[10:30:00] [Server thread/INFO]: System chat: Steve left the game
"""


class LogParserTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        mc = Path(self.tmp.name)
        (mc / "logs").mkdir()
        (mc / "logs" / "latest.log").write_text(LOG)
        (mc / "usercache.json").write_text(json.dumps([{"name": "Steve", "uuid": "x"}, {"name": "Alex", "uuid": "y"}]))
        self.data = LogParser(Config(minecraft_dir=mc)).parse()

    def tearDown(self):
        self.tmp.cleanup()

    def test_private_messages_are_never_shown(self):
        self.assertFalse(any("/msg" in c["c"] for c in self.data["commands"]))
        self.assertNotIn("secret", json.dumps(self.data))

    def test_ip_addresses_are_never_kept(self):
        self.assertNotIn("203.0.113.7", json.dumps(self.data))
        self.assertEqual(self.data["logins"], [{"t": self.data["logins"][0]["t"], "p": "Steve"}])

    def test_coordinates_are_hidden(self):
        self.assertIn("/tp [x y z]", [c["c"] for c in self.data["commands"]])

    def test_admin_commands_only_count_with_operator_rights(self):
        by_cmd = {c["c"]: c for c in self.data["commands"]}
        self.assertTrue(by_cmd["/tp [x y z]"]["tried"])  # not an operator yet
        self.assertTrue(by_cmd["/gamemode creative"]["admin"])  # operator by then
        self.assertEqual(self.data["ever_ops"], ["Steve"])

    def test_sessions_advancements_and_deaths(self):
        p = self.data["profiles"]["Steve"]
        self.assertEqual(p["sessions"], 1)
        self.assertEqual(p["longest"], 30 * 60)
        self.assertEqual(sum(p["per_hour"]), 30 * 60)
        self.assertEqual(p["advancements"][0]["a"], "Diamonds!")
        self.assertEqual([d["m"] for d in p["deaths"]], ["was slain by Zombie"])  # console output is not a death
        self.assertFalse(p["online"])

    def test_moderation(self):
        self.assertEqual(self.data["moderation"][0]["a"], "whitelist_add")


if __name__ == "__main__":
    unittest.main()
