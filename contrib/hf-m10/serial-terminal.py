#!/usr/bin/env python3
"""Local interactive ACM terminal, 115200 8N1. Ctrl+] closes it. No logging."""

import argparse, os, select, sys, termios, tty
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("device", nargs="?")
a = p.parse_args()
if not a.device:
    devices = list(Path("/dev/serial/by-id").glob("usb-CMCC_*HF-M10*"))
    devices += list(Path("/dev/serial/by-id").glob("usb-Lotus_Mini_*"))
    if len(devices) != 1:
        p.error("specify the one CMCC HF-M10 serial device to use")
    a.device = str(devices[0])
if not sys.stdin.isatty():
    p.error("run this from an interactive terminal")
fd = os.open(a.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
local = termios.tcgetattr(sys.stdin)
try:
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0
    attrs[1] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    print("Connected. Ctrl+] exits. Press Enter for login.", flush=True)
    tty.setraw(sys.stdin)
    while True:
        ready, _, _ = select.select([sys.stdin, fd], [], [])
        if fd in ready:
            try:
                data = os.read(fd, 4096)
            except BlockingIOError:
                continue
            if not data:
                break
            os.write(sys.stdout.fileno(), data)
        if sys.stdin in ready:
            data = os.read(sys.stdin.fileno(), 4096)
            if not data or b"\x1d" in data:
                break
            os.write(fd, data)
finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, local)
    os.close(fd)
    print("\nDisconnected.")
