import unittest

from mcstats.progress import gear_points, mc_level, mob_variety_points, progress
from mcstats.stats import fun_stats


class LevelTest(unittest.TestCase):
    def test_minecraft_experience_formula(self):
        # known values from the game: level 16 = 352 XP, level 30 = 1395 XP
        self.assertEqual(mc_level(352)[0], 16)
        self.assertEqual(mc_level(1394)[0], 29)
        self.assertEqual(mc_level(1395)[0], 30)
        self.assertEqual(mc_level(0), (0, 0.0))


class PointsTest(unittest.TestCase):
    def test_farming_one_mob_counts_less_than_variety(self):
        farm = mob_variety_points({"skeleton": 2000})
        variety = mob_variety_points({m: 40 for m in ("zombie", "creeper", "spider", "enderman", "witch")})
        self.assertLess(farm, variety)

    def test_gear(self):
        full_netherite = {s: {"id": f"netherite_{p}", "trim": {"material": "gold", "pattern": "dune"}}
                          for s, p in (("head", "helmet"), ("chest", "chestplate"), ("legs", "leggings"), ("feet", "boots"))}
        self.assertGreater(gear_points(full_netherite), gear_points({"head": {"id": "iron_helmet"}}))
        self.assertEqual(gear_points({"owned": {"totem_of_undying": 10}}), 90)  # max 3 totems count

    def test_progress_is_not_playtime(self):
        stats = {"Busy": {"minecraft:mined": {"minecraft:diamond_ore": 50}, "minecraft:custom": {"minecraft:play_time": 20 * 3600}},
                 "Idle": {"minecraft:custom": {"minecraft:play_time": 20 * 360000}}}
        fun = fun_stats(stats)
        result = progress(fun, stats, {}, {}, {})
        self.assertGreater(result["Busy"]["xp"], result["Idle"]["xp"])


if __name__ == "__main__":
    unittest.main()
