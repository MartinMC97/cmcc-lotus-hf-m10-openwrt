#!/usr/bin/env python3
"""Native HF-M10 runtime regression tests. Never accesses a device."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
CONSOLE=ROOT/'package/cmcc-lotus-hf-m10/cmcc-lotus-hf-m10-console'
DEFAULTS=ROOT/'package/cmcc-lotus-hf-m10/cmcc-lotus-hf-m10-base/files'
TESTS=Path(__file__).resolve().parent
CONTRIB=ROOT/'contrib/hf-m10'
class PartitionTests(unittest.TestCase):
    def resolve(self,entries):
        with tempfile.TemporaryDirectory() as tmp:
            for number,name,start,size in entries:
                node=Path(tmp)/f'rkflash0p{number}'; node.mkdir()
                (node/'uevent').write_text(f'DEVNAME=rkflash0p{number}\nPARTNAME={name}\n')
                (node/'start').write_text(str(start)); (node/'size').write_text(str(size))
            return subprocess.run(['sh','-c','BB=/bin/busybox; [ -x "$BB" ] || BB="'+str(TESTS/'bb-host')+'"; . "$1"; lotus_partition rootfs 53248 71680','test',str(CONSOLE/'files/bootstrap/lotus-partitions')],env={**os.environ,'LOTUS_SYS_BLOCK':tmp},capture_output=True,text=True)
    def test_renumbered(self):
        self.assertEqual(self.resolve([(5,'rootfs',53248,71680)]).stdout.strip(),'/dev/rkflash0p5')
    def test_wrong_geometry(self):
        self.assertNotEqual(self.resolve([(6,'rootfs',53249,71680)]).returncode,0)
    def test_duplicate(self):
        self.assertNotEqual(self.resolve([(5,'rootfs',53248,71680),(6,'rootfs',53248,71680)]).returncode,0)
    def test_name_required(self):
        self.assertNotEqual(self.resolve([(6,'other',53248,71680)]).returncode,0)


class LoginTests(unittest.TestCase):
    def login(self,shadow):
        with tempfile.TemporaryDirectory() as tmp:
            fixture=Path(tmp)/'shadow'; fixture.write_text(shadow)
            script=(CONSOLE/'files/lotus-console-login').read_text().replace('/etc/shadow',str(fixture)).replace('exec /bin/login','exec /bin/echo LOGIN')
            return subprocess.run(['sh','-c',script],capture_output=True,text=True)
    def test_unset(self): self.assertEqual(self.login('root::0:0:99999:7:::\n').stdout.strip(),'LOGIN -f root')
    def test_set(self): self.assertEqual(self.login('root:$6$testhash:0:0:99999:7:::\n').stdout.strip(),'LOGIN')
    def test_locked(self): self.assertEqual(self.login('root:!:0:0:99999:7:::\n').stdout.strip(),'LOGIN')
    def test_missing(self): self.assertNotEqual(self.login('user::0:0:99999:7:::\n').returncode,0)


class PreinitTests(unittest.TestCase):
    def guard(self, readonly=False, wrong_id=False, flow=False):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); blocks=tmp/'blocks'; blocks.mkdir()
            for number,name,start,size in [(5,'rootfs',53248,71680),(6,'userdata',124928,94175)]:
                node=blocks/f'rkflash0p{number}'; node.mkdir()
                (node/'uevent').write_text(f'DEVNAME=rkflash0p{number}\nPARTNAME={name}\n')
                (node/'start').write_text(str(start)); (node/'size').write_text(str(size))
            identity=tmp/'id'; identity.write_text('stock' if wrong_id else 'lotus-mini-openwrt-upper-v1')
            mounts=tmp/'mounts'; mounts.write_text('overlay / overlay rw,lowerdir=/lotus-lower,upperdir=/lotus-upper/lotus-openwrt-v1/upper,workdir=/lotus-upper/lotus-openwrt-v1/work 0 0\n/dev/rkflash0p5 /rom squashfs ro 0 0\n/dev/rkflash0p6 /overlay ext4 '+('ro' if readonly else 'rw')+' 0 0\n')
            hook=(CONSOLE/'files/69_lotus_premounted').read_text().replace('/overlay/lotus-openwrt-v1/id',str(identity)).replace('/proc/self/mounts',str(mounts)).replace('/lib/lotus/partitions.sh',str(CONSOLE/'files/bootstrap/lotus-partitions')).replace('BB=/bin/busybox','BB='+str(TESTS/'bb-host'))
            script='boot_hook_add() { :; }; boot_run_hook() { echo CONFIG_GENERATE; }; preinit_ip_deconfig() { :; };\n'+hook
            if flow:
                script+='\nlotus_premounted_log() { :; }; LOTUS_PREMOUNTED_ROOT=1; preinit_main_hook=remaining; lotus_premounted_test; test -z "$preinit_main_hook"\n'
                script=script.replace("echo 'lotus-preinit: verified NAND overlay; mount_root skipped' > /dev/kmsg",':')
            else: script+='\nlotus_premounted_valid\n'
            return subprocess.run(['sh','-c',script],env={**os.environ,'LOTUS_SYS_BLOCK':str(blocks)},capture_output=True,text=True)
    def test_renumbered_root(self): self.assertEqual(self.guard().returncode,0)
    def test_readonly_overlay(self): self.assertNotEqual(self.guard(readonly=True).returncode,0)
    def test_identity(self): self.assertNotEqual(self.guard(wrong_id=True).returncode,0)
    def test_skip_mount_root(self):
        result=self.guard(flow=True); self.assertEqual(result.returncode,0); self.assertEqual(result.stdout.strip(),'CONFIG_GENERATE')


class GadgetTests(unittest.TestCase):
    def recover(self, ready, competing=False, bound=""):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp); gadget=config/'usb_gadget/cmcc-lotus-hf-m10'
            (gadget/'configs/c.1').mkdir(parents=True)
            (gadget/'functions/acm.console').mkdir(parents=True)
            (gadget/'functions/ffs.adb').mkdir()
            (gadget/'configs/c.1/acm.console').symlink_to('../../functions/acm.console')
            (gadget/'functions/ffs.adb/ready').write_text(str(ready))
            (gadget/'UDC').write_text(bound)
            (gadget/'strings/0x409').mkdir(parents=True)
            serial=gadget/'strings/0x409/serialnumber'; serial.write_text('UNCHANGED_IDENTITY')
            if competing:
                other=config/'usb_gadget/other'; other.mkdir(); (other/'UDC').write_text('ff400000.usb')
            script=(CONSOLE/'files/lotus-usb-gadget').read_text().replace('config=/sys/kernel/config','config='+str(config))
            script=script.replace('grep -q " $config configfs " /proc/mounts || mount -t configfs configfs "$config"', ': # fixture is already mounted')
            result=subprocess.run(['sh','-c',script,'test','start'],capture_output=True,text=True)
            return result.returncode,(gadget/'UDC').read_text(),serial.read_text()
    def test_adopt_bound_composite(self):
        status,bound,serial=self.recover(1,bound='ff400000.usb')
        self.assertEqual(status,0); self.assertEqual(bound,'ff400000.usb'); self.assertEqual(serial,'UNCHANGED_IDENTITY')
    def test_reject_unexpected_controller(self):
        status,bound,_=self.recover(1,bound='another-controller')
        self.assertNotEqual(status,0); self.assertEqual(bound,'another-controller')
    def test_wait_for_functionfs_descriptors(self):
        status,bound,serial=self.recover(0)
        self.assertNotEqual(status,0); self.assertEqual(bound,''); self.assertEqual(serial,'UNCHANGED_IDENTITY')
    def test_rebind_preserves_usb_identity(self):
        status,bound,serial=self.recover(1)
        self.assertEqual(status,0); self.assertEqual(bound.strip(),'ff400000.usb'); self.assertEqual(serial,'UNCHANGED_IDENTITY')
    def test_refuse_competing_owner(self):
        status,bound,_=self.recover(1,True)
        self.assertNotEqual(status,0); self.assertEqual(bound,'')


class RuntimeTargetTests(unittest.TestCase):
    def target(self, kind, value=None):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'tmp').mkdir()
            if kind=='link': (root/'run').symlink_to(value)
            if kind=='dir': (root/'run').mkdir()
            if kind=='file': (root/'run').write_text('preserve me')
            script='BB="'+str(TESTS/'bb-host')+'"; . "$1"; lotus_run_target "$2"'
            r=subprocess.run(['sh','-c',script,'test',str(CONSOLE/'files/bootstrap/lotus-run-targets'),str(root)],capture_output=True,text=True)
            link=(root/'run').readlink() if (root/'run').is_symlink() else None
            return r.returncode,r.stdout.strip().replace(str(root),'NEWROOT'),link
    def test_absolute_var_alias_stays_inside_newroot(self):
        status,target,link=self.target('link','/var/run')
        self.assertEqual(status,0); self.assertEqual(target,'NEWROOT/tmp/run'); self.assertEqual(str(link),'/var/run')
    def test_relative_tmp_alias(self):
        status,target,_=self.target('link','tmp/run')
        self.assertEqual(status,0); self.assertEqual(target,'NEWROOT/tmp/run')
    def test_directory_retained(self):
        status,target,_=self.target('dir')
        self.assertEqual(status,0); self.assertEqual(target,'NEWROOT/run')
    def test_missing_gets_compatible_alias(self):
        status,target,link=self.target('missing')
        self.assertEqual(status,0); self.assertEqual(target,'NEWROOT/tmp/run'); self.assertEqual(str(link),'tmp/run')
    def test_unexpected_link_or_file_rejected(self):
        self.assertNotEqual(self.target('link','/outside/run')[0],0)
        self.assertNotEqual(self.target('file')[0],0)


class SourceTests(unittest.TestCase):
    def test_shell_syntax(self):
        for path in list((CONSOLE/'files/bootstrap').iterdir())+list((CONSOLE/'files').iterdir()):
            if path.is_file(): subprocess.run(['sh','-n',str(path)],check=True)
    def test_direct_has_no_fallback_or_legacy(self):
        text=(CONSOLE/'files/bootstrap/init').read_text()
        self.assertIn('exec "$BB" switch_root',text)
        for name in ('chroot','adbd','ffs.adb','mkfs','reboot','ram-upper','mount --bind'):
            self.assertNotIn(name,text)
        self.assertLess(text.index('mount --move /lotus-upper'),text.index('exec "$BB" switch_root'))


class UserdataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root/'userdata'; self.data.mkdir()
        self.namespace = self.data/'lotus-openwrt-v1'
        self.bb = self.root/'bb'
        # Real filesystem operations, except host chown: tests run unprivileged.
        self.bb.write_text('#!/bin/sh\nif [ "$1" = chown ]; then exit 0; fi\nexec "$@"\n')
        self.bb.chmod(0o755)

    def run_helper(self, action='prepare'):
        return subprocess.run(['sh','-c','BB="$1"; . "$2"; lotus_userdata_'+action+' "$3"',
                               'test',str(self.bb),str(CONSOLE/'files/bootstrap/lotus-userdata'),str(self.data)],
                              capture_output=True,text=True)

    def initialize(self):
        result=self.run_helper(); self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual((self.namespace/'id').read_text(),'lotus-mini-openwrt-upper-v1\n')

    def test_factory_files_preserved_and_root_traversable(self):
        (self.data/'factory-private').write_bytes(b'unchanged')
        self.initialize()
        self.assertEqual((self.data/'factory-private').read_bytes(),b'unchanged')
        self.assertEqual((self.namespace/'upper').stat().st_mode&0o777,0o755)
        self.assertEqual((self.namespace/'id').stat().st_mode&0o777,0o600)
        self.assertFalse((self.namespace/'id.pending').exists())

    def test_existing_settings_and_apps_are_untouched(self):
        self.initialize(); file=self.namespace/'upper/config'; file.write_bytes(b'settings and apps')
        before={str(p): (p.read_bytes(),p.stat().st_mtime_ns) for p in (self.namespace/'id',file)}
        self.assertEqual(self.run_helper().returncode,0)
        self.assertEqual(before,{str(p): (p.read_bytes(),p.stat().st_mtime_ns) for p in (self.namespace/'id',file)})

    def test_resume_after_each_uncommitted_creation(self):
        self.namespace.mkdir()
        for stage in ('directory','upper','work','pending'):
            if stage in ('upper','work'): (self.namespace/stage).mkdir()
            if stage=='pending': (self.namespace/'id.pending').write_text('')
            self.assertEqual(self.run_helper('state').stdout.strip(),'new')
        self.initialize()

    def test_resume_pending_commit(self):
        self.namespace.mkdir(); (self.namespace/'upper').mkdir(); (self.namespace/'work').mkdir()
        (self.namespace/'id.pending').write_text('lotus-mini-openwrt-upper-v1\n')
        self.initialize()

    def test_unknown_namespace_contents_not_adopted(self):
        self.namespace.mkdir(); unknown=self.namespace/'other'; unknown.write_bytes(b'keep')
        self.assertNotEqual(self.run_helper().returncode,0)
        self.assertEqual(unknown.read_bytes(),b'keep'); self.assertFalse((self.namespace/'id').exists())

    def test_unmarked_nonempty_upper_not_adopted(self):
        (self.namespace/'upper').mkdir(parents=True); file=self.namespace/'upper/.private';file.write_bytes(b'keep')
        self.assertNotEqual(self.run_helper().returncode,0); self.assertEqual(file.read_bytes(),b'keep')

    def test_wrong_identity_preserved(self):
        self.namespace.mkdir(); (self.namespace/'id').write_text('foreign-root\n')
        self.assertNotEqual(self.run_helper().returncode,0)
        self.assertEqual((self.namespace/'id').read_text(),'foreign-root\n')

    def test_symlinks_rejected_before_any_write(self):
        target=self.root/'outside';target.mkdir();file=target/'preserve';file.write_bytes(b'keep')
        for name in ('namespace','upper','work','id','id.pending'):
            with self.subTest(name=name):
                if name=='namespace': self.namespace.symlink_to(target)
                else:
                    self.namespace.mkdir(); (self.namespace/name).symlink_to(target if name in ('upper','work') else file)
                self.assertNotEqual(self.run_helper().returncode,0); self.assertEqual(file.read_bytes(),b'keep')
                if name=='namespace': self.namespace.unlink()
                else: (self.namespace/name).unlink();self.namespace.rmdir()

    def test_missing_work_on_marked_namespace_is_an_error(self):
        self.initialize();(self.namespace/'work').rmdir()
        self.assertNotEqual(self.run_helper().returncode,0)
        self.assertFalse((self.namespace/'work').exists())

    def test_write_failure_never_commits_identity(self):
        self.bb.write_text('#!/bin/sh\n[ "$1" != mkdir ] || exit 1\nexec "$@"\n')
        self.assertNotEqual(self.run_helper().returncode,0)
        self.assertFalse((self.namespace/'id').exists())


class ManagementDefaultsTests(unittest.TestCase):
    def defaults(self, existing_zone=False):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); log=tmp/'commands'; library=tmp/'functions'; service=tmp/'service'
            library.write_text('config_load() { :; }; config_get() { '+('eval "$1=wwan";' if existing_zone else 'eval "$1=";')+' }; config_foreach() { '+('"$1" existing;' if existing_zone else ':;')+' }\n')
            service.write_text('#!/bin/sh\nprintf "SERVICE %s\\n" "$*" >> "$TEST_LOG"\n');service.chmod(0o755)
            script=(DEFAULTS/'99-lotus-mini').read_text()
            script=script.replace('/lib/functions.sh',str(library)).replace('/etc/init.d/dropbear',str(service)+' dropbear').replace('/etc/init.d/uhttpd',str(service)+' uhttpd').replace('/etc/apk/repositories.d/distfeeds.list',str(tmp/'absent'))
            script='uci() { case "$1" in -q) return 0;; *) printf "UCI %s\\n" "$*" >> "$TEST_LOG";; esac; };\n'+script
            result=subprocess.run(['sh','-c',script],env={**os.environ,'TEST_LOG':str(log)},capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            return log.read_text()

    def test_fresh_station_has_management_without_forwarding(self):
        log=self.defaults()
        self.assertIn('SERVICE dropbear enable',log); self.assertIn('SERVICE uhttpd enable',log)
        self.assertIn('firewall.lotus_management.network=wwan',log)
        self.assertIn('firewall.lotus_management.forward=REJECT',log)
        self.assertIn('firewall.lotus_management_tcp.dest_port=22 80 443',log)

    def test_existing_station_firewall_preserved(self):
        log=self.defaults(existing_zone=True)
        self.assertNotIn('firewall.',log)
        self.assertIn('SERVICE uhttpd enable',log)


class UserdataImageGuardTests(unittest.TestCase):
    def test_reject_unsupported_partition_length_without_creating_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'data.img'
            result=subprocess.run(['python3',str(CONTRIB/'prepare-userdata-image.py'),
                                   '--sectors','94176','--output',str(output)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertFalse(output.exists())

    def test_existing_image_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'data.img';output.write_bytes(b'original data')
            result=subprocess.run(['python3',str(CONTRIB/'prepare-userdata-image.py'),
                                   '--sectors','94175','--output',str(output)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(output.read_bytes(),b'original data')


if __name__=='__main__': unittest.main()
