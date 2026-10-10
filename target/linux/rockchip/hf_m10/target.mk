ARCH:=aarch64
SUBTARGET:=hf_m10
BOARDNAME:=CMCC HF-M10 RK3308 NAND speaker
FEATURES:=audio usb usbgadget gpio fpu squashfs

define Target/Description
  Build firmware for 和家小荷 MINI 10 (HF-M10), device cmcc-lotus-hf-m10.
  NAND/SFTL, Android Boot with switch_root and USB serial console.
endef
