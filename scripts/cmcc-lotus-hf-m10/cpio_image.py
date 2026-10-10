#!/usr/bin/env python3
"""Reproducible newc/XZ initramfs writer used by the current Boot recipe."""
import os
import subprocess

def cpio(tree, target, legacy=False):
    # GNU cpio accepts sorted NUL-separated input; no shell interpolation.
    for path in [tree, *tree.rglob('*')]:
        os.utime(path, (0, 0), follow_symlinks=False)
    listing = b''.join(str(p.relative_to(tree)).encode() + b'\0' for p in sorted(tree.rglob('*')))
    listing = b'.\0' + listing
    archive = subprocess.run(['cpio', '--null', '-o', '--format=newc', '--owner=0:0', '--reproducible'],
                             input=listing, cwd=tree, check=True, capture_output=True).stdout
    with target.open('xb') as out:
        subprocess.run(['xz', '--threads=1', '--check=crc32', '-c'] + (['--armthumb', '--lzma2=dict=8MiB,preset=9e,lc=2,lp=2,pb=2'] if legacy else ['-9e']), input=archive, stdout=out, check=True, env={k:v for k,v in os.environ.items() if k not in ('LD_PRELOAD', 'FAKEROOTKEY')})
