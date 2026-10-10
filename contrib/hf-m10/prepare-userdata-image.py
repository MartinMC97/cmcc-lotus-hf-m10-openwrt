#!/usr/bin/env python3
"""Create an empty ext4 file for explicit first installation. No device access.

Flashing this image replaces Userdata. Never include it in ordinary upgrades.
The boot initramfs creates its own namespace on the first successful boot.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sectors', type=int, choices=(94175, 95711), required=True,
                        help='actual named Userdata partition length, in 512-byte sectors')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = Path(str(args.output)+'.manifest.json')
    if args.output.exists() or manifest.exists():
        parser.error('refusing to overwrite an existing image or manifest')
    for tool in ('mke2fs', 'e2fsck', 'debugfs'):
        if not shutil.which(tool):
            parser.error('host e2fsprogs required: '+tool)
    os.umask(0o077)
    with args.output.open('xb') as output:
        output.truncate(args.sectors*512)
    subprocess.run(['mke2fs', '-q', '-t', 'ext4', '-b', '1024', '-I', '256', '-m', '0',
                    '-O', '^64bit,^metadata_csum,^orphan_file',
                    '-E', 'lazy_itable_init=0,lazy_journal_init=0,root_owner=0:0',
                    '-L', 'lotus-data', str(args.output)], check=True)
    subprocess.run(['e2fsck', '-fn', str(args.output)], check=True)
    if args.output.stat().st_size != args.sectors*512:
        raise ValueError('image size changed')
    # No staged personal data, keys, or initialized overlay are embedded.
    listing = subprocess.check_output(['debugfs', '-R', 'ls -p /', str(args.output)],
                                      stderr=subprocess.DEVNULL, text=True)
    names = {line.split('/')[5] for line in listing.splitlines() if line.startswith('/')}
    if names != {'.', '..', 'lost+found'}:
        raise ValueError('unexpected image contents')
    report = {'status': 'EMPTY_EXT4_OFFLINE_VERIFIED_RUNTIME_UNTESTED',
              'sectors': args.sectors, 'size': args.output.stat().st_size,
              'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
              'use': 'FIRST_INSTALL_ERASES_DATA_NOT_FOR_UPGRADES',
              'namespace': 'created by initramfs on first boot',
              'device_access': False}
    with manifest.open('x') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
