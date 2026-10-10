#!/usr/bin/env python3
"""Verify a native HF-M10 Boot/Rootfs pair without accessing a device."""
import argparse
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import re
import struct
import subprocess

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('hf_m10_image',Path(__file__).with_name('image.py'))
IMAGE=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(IMAGE)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def cpio_files(data):
    files={}; offset=0
    while offset+110 <= len(data):
        header=data[offset:offset+110]
        require(header[:6]==b'070701','unexpected initramfs cpio format')
        fields=[int(header[6+i*8:14+i*8],16) for i in range(13)]
        size,namesize=fields[6],fields[11]
        require(0<namesize<=4096,'invalid cpio name length')
        namebytes=data[offset+110:offset+110+namesize]
        require(len(namebytes)==namesize and namebytes[-1:]==b'\0','truncated cpio name')
        name=namebytes[:-1].decode()
        offset=(offset+110+namesize+3)&~3
        if name=='TRAILER!!!':
            return files
        require(name not in files and not Path(name).is_absolute() and '..' not in Path(name).parts,'unsafe/duplicate cpio name')
        content=data[offset:offset+size]
        require(len(content)==size,'truncated cpio data')
        files[name]=content
        offset=(offset+size+3)&~3
    raise ValueError('missing cpio trailer')


def dtb_root(data):
    magic,total,structures,strings=struct.unpack_from('>4I',data)
    require(magic==0xd00dfeed and total==len(data),'invalid device tree')
    offset=structures; depth=0; properties={}
    while offset+4<=len(data):
        token=struct.unpack_from('>I',data,offset)[0]; offset+=4
        if token==1:
            end=data.index(b'\0',offset); offset=(end+4)&~3; depth+=1
        elif token==2:
            depth-=1
        elif token==3:
            size,nameoffset=struct.unpack_from('>2I',data,offset); offset+=8
            start=strings+nameoffset
            name=data[start:data.index(b'\0',start)].decode()
            value=data[offset:offset+size]
            require(len(value)==size,'truncated device tree property')
            if depth==1: properties[name]=value
            offset=(offset+size+3)&~3
        elif token==4:
            pass
        elif token==9:
            return properties
        else:
            raise ValueError('invalid device tree token')
    raise ValueError('missing device tree end')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['boot','rootfs','output']:
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): parser.error('refusing to overwrite verification evidence')
    boot=args.boot.read_bytes(); root=args.rootfs.read_bytes()
    require(len(boot)==17825792,'Boot must be exactly 17 MiB')
    require(len(root)==36700160 and root[:4]==b'hsqs','Rootfs must be 35 MiB Squashfs')
    components=IMAGE.pack.unwrap(boot)
    require(IMAGE.pack.wrap(*components,limit=len(boot))[0]==boot,'Android header, SHA-1 or padding mismatch')
    kernel,ramdisk,resource=components
    ram=cpio_files(lzma.decompress(ramdisk))
    rootsha=hashlib.sha256(root).hexdigest()
    require(ram['etc/lotus-rootfs-hashes']==f"ROOTFS_PADDED_SHA='{rootsha}'\n".encode(),'Rootfs does not match Boot pairing manifest')
    IMAGE.check_elf(ram['bin/busybox'])
    for name in ['init','lotus-partitions','lotus-run-targets','lotus-userdata']:
        require(ram[name]==(IMAGE.BOARD/'bootstrap'/name).read_bytes(),'initramfs source mismatch: '+name)
    require(b'switch_root' in ram['init'] and b'chroot' not in ram['init'],'unexpected root handoff')
    require(b'adbd' not in ram['init'],'unexpected ADB bootstrap')
    require(resource[:4]==b'RSCE','missing Rockchip resource container')
    position=resource.find(b'\xd0\x0d\xfe\xed')
    require(position>=0,'missing embedded device tree')
    total=struct.unpack_from('>I',resource,position+4)[0]
    properties=dtb_root(resource[position:position+total])
    require(properties.get('model')==b'HF-M10\0','wrong OpenWrt device model')
    require(properties.get('compatible',b'').split(b'\0')[0]==b'cmcc,lotus-hf-m10','wrong primary board identity')
    host=ROOT/'staging_dir/host/bin'
    def readfile(name):
        return subprocess.check_output([str(host/'unsquashfs4'),'-cat',str(args.rootfs.resolve()),name],stderr=subprocess.DEVNULL)
    require(readfile('usr/libexec/busybox-hf-m10')==ram['bin/busybox'],'console and bootstrap BusyBox differ')
    gadget=(IMAGE.BOARD/'lotus-usb-gadget').read_bytes()
    require(ram['lotus-usb-gadget']==gadget and readfile('usr/libexec/lotus-usb-gadget')==gadget,'USB gadget source differs between ROM, initramfs and source')
    defaults=ROOT/'package/cmcc-lotus-hf-m10/cmcc-lotus-hf-m10-base/files/99-cmcc-lotus-hf-m10'
    require(readfile('etc/uci-defaults/99-cmcc-lotus-hf-m10')==defaults.read_bytes(),'board defaults source mismatch')
    release=readfile('etc/openwrt_release').decode()
    require("DISTRIB_RELEASE='25.12.5'" in release and "DISTRIB_TARGET='rockchip/hf_m10'" in release,'wrong release/target')
    require(readfile('etc/apk/arch').strip()==b'aarch64_generic','wrong package architecture')
    shadow=readfile('etc/shadow').decode()
    passwords=[line.split(':')[1] for line in shadow.splitlines() if line.startswith('root:')]
    require(len(passwords)==1 and passwords[0] in ('','!','*'),'embedded root password')
    listing=subprocess.check_output([str(host/'unsquashfs4'),'-ll',str(args.rootfs.resolve())],text=True)
    paths=[line.split()[-1].removeprefix('squashfs-root/') for line in listing.splitlines() if 'squashfs-root/' in line and ' -> ' not in line]
    require(not any(Path(name).name=='adbd' or name=='openwrt-shell' or re.search(r'etc/dropbear/.*_host_key$',name) for name in paths),'legacy runtime or private SSH key in Rootfs')
    modules=[name for name in paths if name.startswith('lib/modules/') and name.endswith('.ko')]
    require(bool(modules) and all(name.startswith('lib/modules/6.12.108/') for name in modules),'wrong kernel module version')
    for name in modules:
        binary=readfile(name)
        require(binary[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',binary,18)[0]==183,'non-AArch64 kernel module: '+name)
    for name in ['etc/init.d/dropbear','etc/init.d/uhttpd','etc/init.d/rpcd','etc/init.d/lotus-console','lib/preinit/79_lotus_switch_root']:
        require(name in paths,'required management/startup file missing: '+name)
    kernel_image=subprocess.check_output([str(host/'lz4'),'-d','-c'],input=kernel,stderr=subprocess.DEVNULL)
    require(b'Linux version 6.12.108' in kernel_image,'wrong embedded Linux version')
    report={'status':'NATIVE_HF_M10_OFFLINE_PAIR_MODEL_RELEASE_ELF_AND_SOURCE_PASS','device':'cmcc-lotus-hf-m10','model':'HF-M10','release':'25.12.5','kernel':'6.12.108','boot_sha256':hashlib.sha256(boot).hexdigest(),'rootfs_sha256':rootsha,'modules_checked':len(modules),'runtime_acceptance':False,'device_access':False}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as output:
        json.dump(report,output,indent=2); output.write('\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
