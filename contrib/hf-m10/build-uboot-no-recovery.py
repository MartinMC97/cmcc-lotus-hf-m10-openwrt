#!/usr/bin/env python3
"""Patch pinned OEM U-Boot for volume-up USB Loader and 17 MiB Boot.

Binary derivative, not a U-Boot source build. Never accesses a device.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

STOCK_SHA256 = 'f4128865814b2aa9407389bfaed198ca26142f769a2e1eb703487c39452d58c6'
LOADER_SHA256 = '610bdf5596915494cc6ecf2819199e88768b755834973cabd97b8ab9a2602e83'
OUTPUT_SHA256 = '615a65ebaed99f3065ea868458b323fe0124e9243604c34c777ef0bae11a0d4e'
COPY_SIZE = 0x100000
COMPARE_OFFSET = 0x4a9c
IMAGE_NAME = 'uboot-no-recovery-UNTESTED.img'
# File addresses include the LOADER header. ADRP/ADD pairs redirect
# the four Recovery partition selectors to the existing Boot string.
PATCHES = {
    0x1c700: (0x52800020, 0x52800000), 0x1c7cc: (0x52800020, 0x52800000),
    0x3f0c: (0x90000354, 0xf0000394), 0x3f10: (0x911f7694, 0x91395e94),
    0x5850: (0xd0000333, 0xb0000393), 0x5854: (0x911f7673, 0x91395e73),
    0x58d8: (0xd0000333, 0xb0000393), 0x58dc: (0x911f7673, 0x91395e73),
    0x19d20: (0xd0000293, 0xb00002f3), 0x19d24: (0x911f7673, 0x91395e73),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def crc(data):
    table = []
    for i in range(256):
        value = i << 24
        for _ in range(8):
            value = ((value << 1) ^ (0x04c10db7 if value & 0x80000000 else 0)) & 0xffffffff
        table.append(value)
    result = 0
    for value in data:
        result = ((result << 8) ^ table[((result >> 24) ^ value) & 255]) & 0xffffffff
    return result


def validate(copy):
    require(len(copy) == COPY_SIZE and copy[:8] == b'LOADER  ', 'invalid LOADER copy')
    fields = struct.unpack_from('<6I', copy, 8)
    require(fields[:4] == (0, 0, 0x600000, 601428) and fields[5] == 32,
            'unexpected LOADER header fields')
    require(not any(copy[64:0x800]), 'nonzero LOADER header extension')
    payload = copy[0x800:0x800 + fields[3]]
    require(crc(payload) == fields[4], 'LOADER CRC mismatch')
    require(hashlib.sha256(payload + struct.pack('<III', fields[2], fields[3], fields[5])).digest()
            == copy[32:64], 'LOADER SHA-256 mismatch')


def update_checksums(copy):
    load, size = struct.unpack_from('<II', copy, 16)
    hashlen = struct.unpack_from('<I', copy, 28)[0]
    payload = bytes(copy[0x800:0x800 + size])
    struct.pack_into('<I', copy, 24, crc(payload))
    copy[32:64] = hashlib.sha256(payload + struct.pack('<III', load, size, hashlen)).digest()
    validate(copy)


def pointer(data, offset):
    word, add = struct.unpack_from('<II', data, offset)
    require(word & 0x9f000000 == 0x90000000 and add & 0xffc00000 == 0x91000000,
            'unexpected ADRP/ADD instructions')
    require((word & 31) == ((add >> 5) & 31), 'ADRP/ADD register mismatch')
    immediate = ((word >> 5) & 0x7ffff) << 2 | ((word >> 29) & 3)
    if immediate & (1 << 20):
        immediate -= 1 << 21
    address = ((0x600000 + offset - 0x800) & ~4095) + (immediate << 12) + ((add >> 10) & 4095)
    location = address - 0x600000 + 0x800
    require(0 <= location < len(data), 'partition string outside image')
    return bytes(data[location:location + 20]).split(b'\0')[0]


def loader_input(source):
    digest = sha(source)
    require(digest in (STOCK_SHA256, LOADER_SHA256), 'input is not a pinned OEM/volume-up U-Boot')
    require(len(source) == 2 * COPY_SIZE and source[:COPY_SIZE] == source[COPY_SIZE:],
            'expected two identical 1 MiB copies')
    validate(source[:COPY_SIZE])
    copy = bytearray(source[:COPY_SIZE])
    if digest == STOCK_SHA256:
        require(struct.unpack_from('<I', copy, COMPARE_OFFSET)[0] == 0x7100781f,
                'unexpected OEM ADC threshold instruction')
        # cmp w0, #30 -> cmp w0, #200: volume-up, not volume-down/idle.
        struct.pack_into('<I', copy, COMPARE_OFFSET, 0x7103201f)
        update_checksums(copy)
    require(sha(bytes(copy) * 2) == LOADER_SHA256, 'volume-up intermediate digest mismatch')
    return bytes(copy) * 2


def build(source):
    normalized = loader_input(source)
    copy = bytearray(normalized[:COPY_SIZE])
    for offset, (old, new) in PATCHES.items():
        require(struct.unpack_from('<I', copy, offset)[0] == old, 'instruction mismatch at ' + hex(offset))
        struct.pack_into('<I', copy, offset, new)
    for offset in (0x3f0c, 0x5850, 0x58d8, 0x19d20):
        require(pointer(normalized, offset) == b'recovery' and pointer(copy, offset) == b'boot',
                'Recovery selector was not redirected to Boot')
    for start, end in ((0x30b8, 0x3138), (0x4a08, 0x4ad0), (0x6bfd8, 0x6bfe6)):
        require(copy[start:end] == normalized[start:end], 'protected Loader/BCB branch changed')
    require(struct.unpack_from('<I', copy, COMPARE_OFFSET)[0] == 0x7103201f,
            'volume-up Loader threshold was lost')
    update_checksums(copy)
    allowed = (set(range(24, 28)) | set(range(32, 64))
               | set(range(COMPARE_OFFSET, COMPARE_OFFSET + 4))
               | {index for offset in PATCHES for index in range(offset, offset + 4)})
    require(all(index in allowed for index, (before, after)
                in enumerate(zip(source[:COPY_SIZE], copy)) if before != after),
            'unexpected byte changes')
    image = bytes(copy) * 2
    require(sha(image) == OUTPUT_SHA256, 'final U-Boot digest mismatch')
    validate(image[COPY_SIZE:])
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='new output directory')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('refusing to overwrite output directory')
    source = args.input.read_bytes()
    image = build(source)
    report = {
        'status': 'OFFLINE_PINNED_CONTAINER_AND_BRANCH_CHECKS_PASS_RUNTIME_UNTESTED',
        'source_sha256': sha(source), 'loader_intermediate_sha256': LOADER_SHA256,
        'sha256': sha(image), 'volume_up_adc_threshold': 200,
        'instruction_patches': {hex(offset): [hex(old), hex(new)] for offset, (old, new) in PATCHES.items()},
        'volume_up_instruction_patch': {'offset': hex(COMPARE_OFFSET), 'instruction': '0x7103201f'},
        'recovery_mode': 'environment, BCB and SRAM map to normal; four Recovery selectors use Boot',
        'adc_selector_and_usb_loader_branch_unchanged': True, 'identical_copies': True,
        'ddr_loader_trust_sftl_modified': False,
        'required_runtime': ['normal boot', 'cold volume-up plus USB enters Loader',
                             'no-USB volume-up boots normally', 'complete U-Boot readback'],
    }
    args.output.mkdir(parents=True)
    (args.output / IMAGE_NAME).write_bytes(image)
    (args.output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'SHA256SUMS').write_text(''.join(
        sha(path.read_bytes()) + '  ' + path.name + '\n'
        for path in sorted(args.output.iterdir()) if path.is_file()))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
