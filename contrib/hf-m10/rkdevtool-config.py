#!/usr/bin/env python3
"""Validate RKDevTool templates and construct explicitly selected image rows."""
import struct

HEADER=29; RECORD=610; PATH_OFFSET=82; ADDRESS=602; SELECTED=606
ROWS=[('Loader',0),('Parameter',0),('Uboot',0x2000),('trust',0x3000),('Misc',0x4000),('Recovery',0x4800),('Boot',0xa800),('Rootfs',0xd000),('oem',0),('userdata',0x1e800)]

def config(template,selections):
    data=bytearray(template)
    if len(data)!=HEADER+10*RECORD or data[:4]!=b'CFG\0' or data[22]!=10: raise ValueError('unqualified RKDevTool template')
    for index,(name,lba) in enumerate(ROWS):
        offset=HEADER+index*RECORD
        data[offset+PATH_OFFSET:offset+ADDRESS]=bytes(ADDRESS-PATH_OFFSET)
        struct.pack_into('<II',data,offset+ADDRESS,lba,int(name in selections))
        if name in selections:
            encoded=selections[name].encode('utf-16le')+b'\0\0'
            if len(encoded)>ADDRESS-PATH_OFFSET: raise ValueError('path too long')
            data[offset+PATH_OFFSET:offset+PATH_OFFSET+len(encoded)]=encoded
    selected={name for i,(name,_) in enumerate(ROWS) if struct.unpack_from('<I',data,HEADER+i*RECORD+SELECTED)[0]}
    if selected!=set(selections) or selected-set(('Recovery','Boot','Rootfs')): raise ValueError('unsafe selections')
    return data
