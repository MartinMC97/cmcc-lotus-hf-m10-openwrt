#!/usr/bin/env python3
"""Static format tests; no device accesses."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('packer', Path(__file__).resolve().parents[2]/'scripts/cmcc-lotus-hf-m10/pack_android.py')
packer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packer)


class BootFormatTests(unittest.TestCase):
    def setUp(self):
        self.components = (b'\x04\x22\x4d\x18' + bytes(2045),
                           b'\xfd7zXZ\x00' + bytes(313), b'RSCE' + bytes(4093))

    def test_roundtrip(self):
        image, used = packer.wrap(*self.components)
        self.assertEqual(len(image), packer.BOOT_SIZE)
        self.assertEqual(used % packer.PAGE, 0)
        self.assertEqual(packer.unwrap(image), self.components)
        self.assertEqual(image, packer.wrap(*self.components)[0])

    def test_reject_overflow(self):
        with self.assertRaises(ValueError):
            packer.wrap(*self.components, limit=2048)

    def test_ram_mode_header_and_components(self):
        image, _ = packer.wrap(*self.components, root_mode='ram')
        self.assertIn(b'lotus.root=ram', image[:packer.PAGE])
        self.assertEqual(packer.unwrap(image), self.components)
        with self.assertRaises(ValueError):
            packer.wrap(*self.components, root_mode='invalid')

    def test_reject_wrong_formats(self):
        for index in range(3):
            bad = list(self.components)
            bad[index] = b'invalid'
            with self.assertRaises(ValueError):
                packer.wrap(*bad)



if __name__ == '__main__':
    unittest.main()
