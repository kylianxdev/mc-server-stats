import json
import unittest

from mcstats import demo
from mcstats.region import _heightmap, section_blocks, standing_spot, valley, visible


def pack(indexes, bits):
    """Pack palette indexes into longs the way Minecraft does (no index spans two longs)."""
    per_long, longs = 64 // bits, []
    for i in range(0, len(indexes), per_long):
        v = 0
        for j, idx in enumerate(indexes[i:i + per_long]):
            v |= idx << (j * bits)
        longs.append(v - (1 << 64) if v >= 1 << 63 else v)  # NBT longs are signed
    return longs


class SectionTest(unittest.TestCase):
    def test_unpack(self):
        indexes = [i % 3 for i in range(4096)]
        section = {"block_states": {"palette": [{"": "minecraft:air"}, {"Name": "minecraft:stone"}, "minecraft:dirt"],
                                    "data": pack(indexes, 4)}}
        palette, props, at = section_blocks(section)
        self.assertEqual(palette, ["air", "stone", "dirt"])
        self.assertEqual([at(i) for i in (0, 1, 2, 4095)], [0, 1, 2, 4095 % 3])

    def test_single_block(self):
        palette, props, at = section_blocks({"block_states": {"palette": ["minecraft:stone"]}})
        self.assertEqual((palette, at(1234)), (["stone"], 0))


class VisibleTest(unittest.TestCase):
    def test_hidden_blocks_are_left_out(self):
        # a 3×3×3 cube of stone on a 5×5 field: the middle block can't be seen, the sides can
        columns = {(x, z): {0: "grass_block"} for x in range(-1, 4) for z in range(-1, 4)}
        for x in range(3):
            for z in range(3):
                columns[(x, z)] = {y: "stone" for y in range(1, 4)}
        out = visible(columns, {}, (0, 0, 0), below=5)
        blocks = [out["blocks"][i:i + 4] for i in range(0, len(out["blocks"]), 4)]
        stone = [b[:3] for b in blocks if out["palette"][b[3]] == "stone"]
        self.assertEqual(len(stone), 26)
        self.assertNotIn([1, 2, 1], stone)
        self.assertEqual(out["surface"]["1,1"], 3)

    def test_outside_is_not_drawn(self):
        # the walls on the edge of the area face away from the camera: they are left out
        columns = {(x, z): {y: "stone" for y in range(3)} for x in range(3) for z in range(3)}
        out = visible(columns, {}, (0, 0, 0), below=5)
        blocks = [out["blocks"][i:i + 4] for i in range(0, len(out["blocks"]), 4)]
        self.assertNotIn([0, 1, 1, 0], blocks)

    def test_slab_halves(self):
        out = visible({(0, 0): {0: "oak_slab"}}, {(0, 0, 0): {"type": "top"}}, (0, 0, 0))
        self.assertEqual(out["palette"], ["oak_slab:top"])

    def test_demo_world(self):
        out = json.loads(demo.world3d())
        w, d = out["size"]
        self.assertEqual(len(out["h"]), w * d)
        self.assertGreater(len(out["detail"]), 1000)
        self.assertIn("water", out["palette"])
        self.assertEqual(set(out["homes"]), {"Steve", "Alex", "Noor", "Kai"})


class ValleyTest(unittest.TestCase):
    def test_heightmap(self):
        # 37 longs of 7 entries of 9 bits, like a chunk of a 384 blocks high world
        values = [i % 300 for i in range(256)]
        longs = [sum(v << (9 * j) for j, v in enumerate(values[i:i + 7])) for i in range(0, 256, 7)]
        self.assertEqual(_heightmap(longs), values)

    def test_no_real_coordinates(self):
        ground = lambda x, z: 70
        block = lambda x, y, z: ("grass_block" if y <= 70 else "air", {})
        out = valley(ground, block, (1000, -2000), {"Steve": (1010, 71, -1990)}, margin=4)
        self.assertEqual(out["homes"]["Steve"][0::2], [10, 10])
        self.assertTrue(all(abs(v) < 100 for v in out["detail"]))
        self.assertEqual(out["origin"], [-14, -14])

    def test_standing_spot_is_outside(self):
        # a roof over the bed: the player stands next to the house, not on top of it
        roof = {(x, z) for x in range(-2, 3) for z in range(-2, 3)}
        spot = standing_spot(lambda x, z: 74 if (x, z) in roof else 70, (0, 71, 0))
        self.assertNotIn((spot[0], spot[2]), roof)
        self.assertEqual(spot[1], 71)


if __name__ == "__main__":
    unittest.main()
