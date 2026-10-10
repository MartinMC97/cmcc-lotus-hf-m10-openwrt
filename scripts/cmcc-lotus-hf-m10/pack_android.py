#!/usr/bin/env python3
"""Experimental Android boot v0 wrapper, never a flash/install utility."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

PAGE = 2048
BOOT_SIZE = 5242880
ROOTFS_SIZE = 36700160
CMDLINE = 'console=ttyS2,1500000n8 rdinit=/init loglevel=8 ignore_loglevel panic=3 oops=panic clk_ignore_unused lotus.root=nand'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def wrap(kernel, ramdisk, resource, limit=BOOT_SIZE, root_mode='nand'):
    if root_mode not in ('nand', 'ram'):
        raise ValueError('root mode must be nand or ram')
    if not kernel.startswith(b'\x04\x22\x4d\x18'):
        raise ValueError('kernel must use the validated LZ4 frame, not legacy/raw Image')
    if not ramdisk.startswith(b'\xfd7zXZ\x00'):
        raise ValueError('ramdisk must be XZ compressed')
    if not resource.startswith(b'RSCE'):
        raise ValueError('second component must be Rockchip RSCE resource')
    components = (kernel, ramdisk, resource)
    ident = hashlib.sha1()
    for data in components:
        ident.update(data)
        ident.update(struct.pack('<I', len(data)))
    header = struct.pack('<8s10I16s512s32s1024s', b'ANDROID!',
                         len(kernel), 0x10008000, len(ramdisk), 0x11000000,
                         len(resource), 0x10f00000, 0x10000100, PAGE, 0, 0,
                         b'', CMDLINE.replace('lotus.root=nand', f'lotus.root={root_mode}').encode(), ident.digest(), b'')
    payload = header.ljust(PAGE, b'\0')
    for data in components:
        payload += data + bytes((-len(data)) % PAGE)
    used = len(payload)
    if used > limit:
        raise ValueError(f'Boot payload {used} exceeds partition {limit}; do not truncate')
    return payload.ljust(limit, b'\0'), used


def unwrap(image):
    fields = struct.unpack_from('<8s10I', image)
    if fields[0] != b'ANDROID!' or fields[8:11] != (PAGE, 0, 0):
        raise ValueError('unexpected boot geometry/header')
    result = []
    offset = PAGE
    for size in (fields[1], fields[3], fields[5]):
        result.append(image[offset:offset + size])
        offset += (size + PAGE - 1) // PAGE * PAGE
    return tuple(result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel', 'ramdisk', 'resource', 'rootfs', 'output', 'manifest'):
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--root-mode', choices=('nand', 'ram'), default='nand')
    a = p.parse_args()
    if a.output.exists() or a.manifest.exists():
        p.error('refusing to overwrite output or manifest')
    components = tuple(path.read_bytes() for path in (a.kernel, a.ramdisk, a.resource))
    root = a.rootfs.read_bytes()
    if not root.startswith(b'hsqs') or len(root) > ROOTFS_SIZE:
        p.error('rootfs must be Squashfs and fit the 35 MiB partition')
    padded = root.ljust(ROOTFS_SIZE, b'\0')
    image, used = wrap(*components, root_mode=a.root_mode)
    assert unwrap(image) == components
    manifest = {'status': 'UNTESTED_DO_NOT_FLASH', 'format': 'Android boot v0',
                'page_size': PAGE, 'boot_size': len(image), 'payload_size': used,
                'root_mode': a.root_mode,
                'headroom': BOOT_SIZE - used, 'boot_sha256': sha(image),
                'rootfs_input_size': len(root), 'rootfs_input_sha256': sha(root),
                'rootfs_padded_size': ROOTFS_SIZE, 'rootfs_padded_sha256': sha(padded),
                'components': {name: {'size': len(data), 'sha256': sha(data)}
                               for name, data in zip(('kernel', 'ramdisk', 'resource'), components)}}
    # Exclusive creation: an older candidate must never be replaced accidentally.
    with a.output.open('xb') as f:
        f.write(image)
    with a.manifest.open('x') as f:
        json.dump(manifest, f, indent=2)
        f.write('\n')
    print('ANDROID_BOOT_STATIC_ROUNDTRIP_PASS_NOT_FLASHABLE')


if __name__ == '__main__':
    main()
