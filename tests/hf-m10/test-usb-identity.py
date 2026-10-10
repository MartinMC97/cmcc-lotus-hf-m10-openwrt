#!/usr/bin/env python3
"""Exercise per-unit CDC identity generation with a temporary configfs fixture."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
GADGET=ROOT/'package/cmcc-lotus-hf-m10/cmcc-lotus-hf-m10-console/files/lotus-usb-gadget'

class UsbIdentity(unittest.TestCase):
    def identity(self, cmdline, cpuinfo=''):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); config=root/'config'; udc=root/'udc'; udc.mkdir()
            command=root/'cmdline'; command.write_text(cmdline)
            cpu=root/'cpuinfo'; cpu.write_text(cpuinfo)
            text=GADGET.read_text().replace('config=/sys/kernel/config','config='+str(config))
            text=text.replace('/proc/cmdline',str(command)).replace('/proc/cpuinfo',str(cpu))
            text=text.replace('grep -q " $config configfs " /proc/mounts || mount -t configfs configfs "$config"',': # configfs fixture')
            text=text.replace('/sys/class/udc/$udc',str(udc))
            result=subprocess.run(['sh','-c',text,'fixture','start'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            device=config/'usb_gadget/cmcc-lotus-hf-m10'
            self.assertEqual((device/'UDC').read_text().strip(),'ff400000.usb')
            self.assertEqual((device/'strings/0x409/product').read_text().strip(),'CMCC HF-M10 OpenWrt console')
            self.assertTrue((device/'configs/c.1/acm.console').is_symlink())
            self.assertFalse((device/'functions/ffs.adb').exists())
            return (device/'strings/0x409/serialnumber').read_text().strip()

    def test_unit_boot_serial_precedes_cpu_serial(self):
        a=self.identity('console=ttyS2 androidboot.serialno=UNIT_A lotus.root=nand','Serial : CPU_SHARED\n')
        b=self.identity('console=ttyS2 androidboot.serialno=UNIT_B lotus.root=nand','Serial : CPU_SHARED\n')
        self.assertEqual(a,'UNIT_A'); self.assertEqual(b,'UNIT_B'); self.assertNotEqual(a,b)

    def test_cpu_serial_fallback(self):
        self.assertEqual(self.identity('console=ttyS2','Serial : CPU_FALLBACK\n'),'CPU_FALLBACK')

    def test_no_embedded_device_identity(self):
        self.assertEqual(self.identity('console=ttyS2'),'CMCCHFM10CONSOLE')

if __name__=='__main__': unittest.main()
