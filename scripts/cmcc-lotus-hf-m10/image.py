#!/usr/bin/env python3
"""Opt-in image recipe for source-built console/direct-root packages; no flash."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

BASE=Path(__file__).resolve().parent
TOPDIR=BASE.parents[1]
BOARD=TOPDIR/'package/cmcc-lotus-hf-m10/cmcc-lotus-hf-m10-console/files'

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,file); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
pack=load('pack',BASE/'pack_android.py')
builder=load('builder',BASE/'cpio_image.py')

def check_elf(binary):
    if binary[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',binary,18)[0]!=183: raise ValueError('AArch64 ELF required')
    offset=struct.unpack_from('<Q',binary,32)[0]; stride,count=struct.unpack_from('<HH',binary,54)
    if stride!=56 or count>64: raise ValueError('unexpected ELF headers')
    for i in range(count):
        if struct.unpack_from('<I',binary,offset+i*stride)[0] in (2,3): raise ValueError('static BusyBox required')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kernel','dtb','rootfs','output'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--boot-size',type=int,choices=(5242880,17825792),default=17825792)
    a=p.parse_args()
    if a.output.exists() or Path(str(a.output)+'.manifest.json').exists(): p.error('refusing to overwrite')
    host=TOPDIR/'staging_dir/host/bin'
    root=a.rootfs.read_bytes()
    if not root.startswith(b'hsqs') or len(root)>pack.ROOTFS_SIZE: raise ValueError('invalid rootfs')
    rootsha=hashlib.sha256(root.ljust(pack.ROOTFS_SIZE,b'\0')).hexdigest()
    with tempfile.TemporaryDirectory(prefix='lotus-direct-recipe-') as directory:
        tmp=Path(directory); ram=tmp/'ram'; ram.mkdir(); (ram/'bin').mkdir()
        bb=subprocess.check_output([str(host/'unsquashfs4'),'-cat',str(a.rootfs),'usr/libexec/busybox-hf-m10'])
        check_elf(bb)
        hook=subprocess.check_output([str(host/'unsquashfs4'),'-cat',str(a.rootfs),'lib/preinit/79_lotus_switch_root'])
        if b'lotus_partition rootfs' not in hook: raise ValueError('direct-root package missing')
        (ram/'bin/busybox').write_bytes(bb); (ram/'bin/busybox').chmod(0o755)
        for applet in ('sh','mount','mkdir','grep','cat','sed','sleep','ln'): (ram/'bin'/applet).symlink_to('busybox')
        for name in ('dev','proc','sys','run','tmp','etc','root','sbin'): (ram/name).mkdir()
        for name in ('init','lotus-partitions','lotus-run-targets','lotus-userdata'): shutil.copyfile(BOARD/'bootstrap'/name,ram/name)
        (ram/'init').chmod(0o755)
        shutil.copyfile(BOARD/'lotus-usb-gadget',ram/'lotus-usb-gadget'); (ram/'lotus-usb-gadget').chmod(0o755)
        (ram/'etc/lotus-rootfs-hashes').write_text(f"ROOTFS_PADDED_SHA='{rootsha}'\n")
        builder.cpio(ram,tmp/'initramfs.cpio.xz')
        subprocess.run([str(host/'lz4'),'-12',str(a.kernel),str(tmp/'Image.lz4')],check=True)
        shutil.copyfile(a.dtb,tmp/'rk-kernel.dtb')
        subprocess.run([str(host/'hf-m10-resource-tool'),'--pack','--image=resource.img','rk-kernel.dtb'],cwd=tmp,check=True)
        components=tuple((tmp/name).read_bytes() for name in ('Image.lz4','initramfs.cpio.xz','resource.img'))
        boot,used=pack.wrap(*components,limit=a.boot_size)
        if pack.unwrap(boot)!=components: raise ValueError('Boot roundtrip failed')
        with a.output.open('xb') as f: f.write(boot)
        report={'status':'BUILT_RUNTIME_UNTESTED', 'device':'cmcc-lotus-hf-m10', 'model':'HF-M10','boot_size':len(boot),'payload_size':used,'headroom':len(boot)-used,
                'boot_sha256':hashlib.sha256(boot).hexdigest(),'rootfs_padded_sha256':rootsha,
                'layout':'stock' if a.boot_size==5242880 else 'no-recovery-17m'}
        with Path(str(a.output)+'.manifest.json').open('x') as f: json.dump(report,f,indent=2); f.write('\n')
        print(json.dumps(report))

if __name__=='__main__': main()
