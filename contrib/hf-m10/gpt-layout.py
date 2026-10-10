#!/usr/bin/env python3
"""Validate/migrate an OFFLINE full SFTL disk dump. No device writes.

Preserve disk/partition GUIDs, other partitions, boot code and all data sectors.
Require both GPT CRCs and tables to agree before producing changed metadata.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

SECTOR = 512
HEADER = struct.Struct('<8sIIIIQQQQ16sQIII')

def parse(data, lba):
    offset = lba * SECTOR
    fields = HEADER.unpack_from(data, offset)
    magic, revision, length, crc, reserved, current, alternate, first, last, guid, entries, count, stride, array_crc = fields
    if (magic, revision, reserved, current) != (b'EFI PART', 0x10000, 0, lba):
        raise ValueError('unexpected GPT header')
    if length != 92 or count != 128 or stride != 128:
        raise ValueError('unqualified GPT geometry')
    header = bytearray(data[offset:offset + length]); struct.pack_into('<I', header, 16, 0)
    if zlib.crc32(header) != crc: raise ValueError('GPT header CRC mismatch')
    table = data[entries * SECTOR:entries * SECTOR + count * stride]
    if len(table) != count * stride or zlib.crc32(table) != array_crc:
        raise ValueError('GPT array CRC mismatch')
    parts = {}
    ranges = []
    for index in range(count):
        entry = table[index * stride:(index + 1) * stride]
        if entry[:16] == bytes(16):
            if any(entry): raise ValueError('nonzero unused GPT entry')
            continue
        start, end = struct.unpack_from('<QQ', entry, 32)
        name = entry[56:128].decode('utf-16le').split('\0')[0]
        if not name or name in parts or not first <= start <= end <= last:
            raise ValueError('duplicate name or invalid extent')
        parts[name] = {'index': index, 'start': start, 'length': end - start + 1}
        ranges.append((start, end))
    ranges.sort()
    if any(a[1] >= b[0] for a,b in zip(ranges,ranges[1:])): raise ValueError('overlapping partitions')
    return fields, table, parts

def validate(data):
    if len(data) % SECTOR or data[510:512] != b'\x55\xaa' or data[450] != 0xee:
        raise ValueError('expected protective MBR and whole disk sectors')
    primary, table, parts = parse(data, 1)
    if not 34 <= primary[6] < len(data) // SECTOR: raise ValueError('backup outside disk')
    backup, second, other = parse(data, primary[6])
    if backup[6] != 1 or primary[7:10] != backup[7:10] or primary[11:] != backup[11:] or table != second:
        raise ValueError('primary and backup GPT disagree')
    if primary[10] != 2 or backup[10] + 32 != backup[5] or primary[7] != 34 or primary[8] != backup[10] - 1:
        raise ValueError('unqualified GPT metadata placement')
    return primary, backup, table, parts

def migrate(data):
    primary, backup, table, parts = validate(data)
    expected = {'uboot': (0x2000,0x1000), 'trust': (0x3000,0x1000), 'misc':(0x4000,0x800),
                'recovery':(0x4800,0x6000), 'boot':(0xa800,0x2800), 'rootfs':(0xd000,0x11800)}
    if set(parts) != set(expected) | {'userdata'}: raise ValueError('unqualified partition names')
    for name, extent in expected.items():
        if (parts[name]['start'], parts[name]['length']) != extent: raise ValueError('stock layout mismatch: '+name)
    if parts['userdata']['start'] != 0x1e800 or parts['userdata']['length'] not in (94175,95711):
        raise ValueError('userdata geometry mismatch')
    entries = []
    for index in range(128):
        entry=bytearray(table[index*128:(index+1)*128])
        if index == parts['recovery']['index']: continue
        if index == parts['boot']['index']: struct.pack_into('<QQ',entry,32,0x4800,0xcfff)
        if any(entry): entries.append(bytes(entry))
    updated=b''.join(entries).ljust(len(table),b'\0')
    result=bytearray(data)
    for fields in (primary,backup):
        entry_offset=fields[10]*SECTOR
        result[entry_offset:entry_offset+len(updated)]=updated
        offset=fields[5]*SECTOR
        struct.pack_into('<I',result,offset+88,zlib.crc32(updated))
        struct.pack_into('<I',result,offset+16,0)
        struct.pack_into('<I',result,offset+16,zlib.crc32(result[offset:offset+fields[2]]))
    _,_,_,after=validate(result)
    for name in ('uboot','trust','misc','rootfs','userdata'):
        if (parts[name]['start'],parts[name]['length']) != (after[name]['start'],after[name]['length']):
            raise ValueError('protected partition moved')
    # Byte-for-byte preservation of everything outside the GPT tables/headers.
    if data[:SECTOR] != result[:SECTOR] or data[34*SECTOR:backup[10]*SECTOR] != result[34*SECTOR:backup[10]*SECTOR] or data[(backup[5]+1)*SECTOR:] != result[(backup[5]+1)*SECTOR:]:
        raise ValueError('data sectors changed')
    return bytes(result), parts, after

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('disk_dump',type=Path)
    p.add_argument('--candidate-directory',type=Path)
    a=p.parse_args()
    if not a.disk_dump.is_file() or a.disk_dump.is_symlink(): p.error('regular offline file required')
    data=a.disk_dump.read_bytes(); primary,backup,table,parts=validate(data)
    if not a.candidate_directory:
        print(json.dumps(parts,indent=2)); return
    out=a.candidate_directory
    if out.exists(): p.error('refusing to overwrite')
    candidate,before,after=migrate(data)
    out.mkdir(parents=True)
    # Metadata fragments only; no automatic device writer or deploy config.
    (out/'primary-gpt.bin').write_bytes(candidate[:34*SECTOR])
    (out/'backup-gpt.bin').write_bytes(candidate[backup[10]*SECTOR:(backup[5]+1)*SECTOR])
    parameter='CMDLINE: mtdparts=rk29xxnand:0x1000@0x2000(uboot),0x1000@0x3000(trust),0x800@0x4000(misc),0x8800@0x4800(boot),0x11800@0xd000(rootfs),0x%x@0x1e800(userdata)\n'%after['userdata']['length']
    (out/'parameter-layout-reference.txt').write_text(parameter)
    report={'status':'OFFLINE_ONLY_DO_NOT_FLASH_UBOOT_AUDIT_PENDING','before':before,'after':after,
            'primary_lba':0,'backup_lba':backup[10],'gpt_alternate_lba':primary[6],'physical_sectors':len(data)//SECTOR,'disk_sha256':hashlib.sha256(data).hexdigest(),
            'candidate_disk_sha256':hashlib.sha256(candidate).hexdigest(),
            'parameter':'layout reference only; not a complete Rockchip parameter image',
            'pending':['rounds 1-3 hardware acceptance','complete offline userdata backup','U-Boot recovery/BCB/no-USB branches audit','Loader/Windows migration and rollback']}
    (out/'layout.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(x.read_bytes()).hexdigest()}  {x.name}\n' for x in sorted(out.iterdir()) if x.is_file()))

if __name__ == '__main__': main()
