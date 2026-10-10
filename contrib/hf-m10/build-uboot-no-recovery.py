#!/usr/bin/env python3
"""Offline pinned stock U-Boot derivative. Never accesses a device."""
import argparse,hashlib,struct,json
from pathlib import Path
ACTIVE='610bdf5596915494cc6ecf2819199e88768b755834973cabd97b8ab9a2602e83'
# Pinned file addresses, including 0x800 LOADER header. Same-page ADRP clones.
PATCHES={0x1c700:(0x52800020,0x52800000),0x1c7cc:(0x52800020,0x52800000),
 0x3f0c:(0x90000354,0xf0000394),0x3f10:(0x911f7694,0x91395e94),
 0x5850:(0xd0000333,0xb0000393),0x5854:(0x911f7673,0x91395e73),
 0x58d8:(0xd0000333,0xb0000393),0x58dc:(0x911f7673,0x91395e73),
 0x19d20:(0xd0000293,0xb00002f3),0x19d24:(0x911f7673,0x91395e73)}
def crc(data):
 table=[]
 for i in range(256):
  n=i<<24
  for _ in range(8):n=((n<<1)^(0x04c10db7 if n&0x80000000 else 0))&0xffffffff
  table.append(n)
 result=0
 for b in data:result=((result<<8)^table[((result>>24)^b)&255])&0xffffffff
 return result
def validate(copy):
 assert len(copy)==0x100000 and copy[:8]==b'LOADER  '
 fields=struct.unpack_from('<6I',copy,8);assert fields[:4]==(0,0,0x600000,601428) and fields[5]==32
 assert not any(copy[64:0x800]);payload=copy[0x800:0x800+fields[3]]
 assert crc(payload)==fields[4]
 assert hashlib.sha256(payload+struct.pack('<III',fields[2],fields[3],fields[5])).digest()==copy[32:64]
def pointer(data,off):
 word=struct.unpack_from('<I',data,off)[0];add=struct.unpack_from('<I',data,off+4)[0]
 assert word&0x9f000000==0x90000000 and add&0xffc00000==0x91000000
 assert (word&31)==((add>>5)&31)
 imm=((word>>5)&0x7ffff)<<2|((word>>29)&3);imm=imm-(1<<21) if imm&(1<<20) else imm
 address=((0x600000+off-0x800)&~4095)+(imm<<12)+((add>>10)&4095)
 file=address-0x600000+0x800
 return bytes(data[file:file+20]).split(b'\0')[0]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():p.error('refusing overwrite')
source=a.input.read_bytes();assert hashlib.sha256(source).hexdigest()==ACTIVE
assert len(source)==0x200000 and source[:0x100000]==source[0x100000:];validate(source[:0x100000])
copy=bytearray(source[:0x100000])
for off,(old,new) in PATCHES.items():assert struct.unpack_from('<I',copy,off)[0]==old;struct.pack_into('<I',copy,off,new)
for off in (0x3f0c,0x5850,0x58d8,0x19d20):assert pointer(source,off)==b'recovery' and pointer(copy,off)==b'boot'
assert copy[0x30b8:0x3138]==source[0x30b8:0x3138] and copy[0x4a08:0x4ad0]==source[0x4a08:0x4ad0]
# All three entry sources (environment, BCB, SRAM recovery #3) map to normal.
assert source[0x6bfd8:0x6bfe6]==copy[0x6bfd8:0x6bfe6] # shared boot-recovery string
load,size=struct.unpack_from('<II',copy,16);hashlen=struct.unpack_from('<I',copy,28)[0];payload=bytes(copy[0x800:0x800+size])
struct.pack_into('<I',copy,24,crc(payload));copy[32:64]=hashlib.sha256(payload+struct.pack('<III',load,size,hashlen)).digest();validate(copy)
allowed=set(range(24,28))|set(range(32,64))|{x for off in PATCHES for x in range(off,off+4)}
assert all(i in allowed for i,(before,after) in enumerate(zip(source,copy)) if before!=after)
a.output.mkdir(parents=True);image=a.output/'uboot-no-recovery-UNTESTED.img';image.write_bytes(bytes(copy)*2);validate(image.read_bytes()[0x100000:])
report={'status':'OFFLINE_PINNED_CONTAINER_AND_BRANCH_CHECKS_PASS_RUNTIME_UNTESTED','source_sha256':ACTIVE,'sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'instruction_patches':{hex(o):[hex(x),hex(y)] for o,(x,y) in PATCHES.items()},'recovery_mode':'environment, BCB and SRAM map to normal; all four recovery partition selectors use boot','key_loader_adc_and_usb_branch_unchanged':True,'identical_copies':True,'ddr_loader_trust_sftl_modified':False,'required_runtime':['stock-layout normal boot','RESTART2 recovery maps to Boot','no-USB volume+ boot maps to Boot','cold volume+ USB Loader','complete U-Boot readback','rollback rehearsal before GPT migration']}
(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n');(a.output/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in sorted(a.output.iterdir()) if f.is_file()));print(json.dumps(report,indent=2))
