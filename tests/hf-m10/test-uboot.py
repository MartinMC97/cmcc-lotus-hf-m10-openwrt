#!/usr/bin/env python3
"""Pinned OEM -> volume-up Loader -> no-Recovery U-Boot, offline only."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'contrib/hf-m10/build-uboot-no-recovery.py'
SPEC = importlib.util.spec_from_file_location('uboot', SCRIPT)
uboot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(uboot)


class UBootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'vendor/hf-m10/uboot-stock.img').read_bytes()
        cls.loader = uboot.loader_input(cls.source)
        cls.result = uboot.build(cls.source)

    def test_input_and_output_are_pinned(self):
        self.assertEqual(hashlib.sha256(self.source).hexdigest(), uboot.STOCK_SHA256)
        self.assertEqual(hashlib.sha256(self.loader).hexdigest(), uboot.LOADER_SHA256)
        self.assertEqual(hashlib.sha256(self.result).hexdigest(), uboot.OUTPUT_SHA256)

    def test_old_volume_up_input_is_supported(self):
        self.assertEqual(uboot.build(self.loader), self.result)

    def test_two_valid_identical_copies(self):
        self.assertEqual(len(self.result), 2 * uboot.COPY_SIZE)
        self.assertEqual(self.result[:uboot.COPY_SIZE], self.result[uboot.COPY_SIZE:])
        for offset in (0, uboot.COPY_SIZE):
            uboot.validate(self.result[offset:offset + uboot.COPY_SIZE])

    def test_loader_threshold_and_recovery_selectors(self):
        self.assertEqual(struct.unpack_from('<I', self.result, uboot.COMPARE_OFFSET)[0], 0x7103201f)
        for offset in (0x3f0c, 0x5850, 0x58d8, 0x19d20):
            self.assertEqual(uboot.pointer(self.result, offset), b'boot')
        for start, end in ((0x30b8, 0x3138), (0x4a08, 0x4ad0)):
            self.assertEqual(self.result[start:end], self.loader[start:end])

    def test_corrupt_input_is_rejected(self):
        for offset in (0, 24, 0x4a9c, 0x104a9c, len(self.source) - 1):
            changed = bytearray(self.source)
            changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                uboot.build(bytes(changed))

    def test_header_validator_rejects_corruption(self):
        for offset in (0, 8, 24, 32, 64, 0x800):
            changed = bytearray(self.result[:uboot.COPY_SIZE])
            changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                uboot.validate(bytes(changed))

    def test_optimized_python_cannot_skip_input_checks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'bad.img').write_bytes(b'not the OEM U-Boot')
            result = subprocess.run([sys.executable, '-O', str(SCRIPT), '--input', str(root / 'bad.img'),
                                     '--output', str(root / 'out')], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'out').exists())

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = subprocess.run([sys.executable, str(SCRIPT), '--input', str(ROOT / 'vendor/hf-m10/uboot-stock.img'),
                                     '--output', str(root)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(root.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
