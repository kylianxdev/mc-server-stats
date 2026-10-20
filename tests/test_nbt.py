import gzip
import struct
import tempfile
import unittest
from pathlib import Path

from mcstats.nbt import read_nbt, read_nbt_file


def s(text):
    raw = text.encode()
    return struct.pack(">H", len(raw)) + raw


def tag(kind, name, payload):
    return bytes([kind]) + s(name) + payload


# {"data": {"Name": "Steve", "Score": 5, "List": [1, 2], "Big": 2**40}}
SAMPLE = tag(10, "", tag(10, "data",
    tag(8, "Name", s("Steve")) + tag(3, "Score", struct.pack(">i", 5))
    + tag(9, "List", bytes([3]) + struct.pack(">i", 2) + struct.pack(">ii", 1, 2))
    + tag(4, "Big", struct.pack(">q", 2**40)) + b"\x00") + b"\x00")


class NbtTest(unittest.TestCase):
    def test_compound(self):
        self.assertEqual(read_nbt(SAMPLE), {"data": {"Name": "Steve", "Score": 5, "List": [1, 2], "Big": 2**40}})

    def test_gzip_file(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.dat"
            f.write_bytes(gzip.compress(SAMPLE))
            self.assertEqual(read_nbt_file(f)["data"]["Name"], "Steve")

    def test_unknown_tag(self):
        with self.assertRaises(ValueError):
            read_nbt(tag(10, "", bytes([99]) + s("x")))


if __name__ == "__main__":
    unittest.main()
