#!/usr/bin/env python3
"""Stock-layout guard constants for the independently tested U-Boot procedure."""
import hashlib

EXPECTED = {
    'uboot': (8192, 4096), 'trust': (12288, 4096), 'misc': (16384, 2048),
    'recovery': (18432, 24576), 'boot': (43008, 10240),
    'rootfs': (53248, 71680), 'userdata': (124928, 94175),
}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
