# SPDX-License-Identifier: GPL-2.0-only

define Build/hf-m10-kernel
	cp $(KDIR)/Image "$@"
endef

define Build/hf-m10-pad-rootfs
	@test $$(stat -c %s "$@") -le 36700160
	truncate -s 36700160 "$@"
endef

define Build/hf-m10-boot
	rm -f "$@" "$@.manifest.json"
	python3 $(TOPDIR)/scripts/cmcc-lotus-hf-m10/image.py \
		--kernel "$(IMAGE_KERNEL)" --dtb "$(KDIR)/image-$(firstword $(DEVICE_DTS)).dtb" \
		--rootfs "$(IMAGE_ROOTFS)" --output "$@" --boot-size 17825792
	cp "$@.manifest.json" "$(BIN_DIR)/$(notdir $@).manifest.json"
endef

define Device/cmcc-lotus-hf-m10
  DEVICE_VENDOR := CMCC
  DEVICE_MODEL := HF-M10
  SOC := rk3308
  DEVICE_DTS := rk3308-cmcc-lotus-hf-m10
  SUPPORTED_DEVICES := cmcc,lotus-hf-m10 lotus,mini-rk3308
  UBOOT_DEVICE_NAME :=
  KERNEL := hf-m10-kernel
  IMAGES := rootfs.squashfs boot.img
  IMAGE/rootfs.squashfs := append-rootfs | check-size 35840k | hf-m10-pad-rootfs
  IMAGE/boot.img := hf-m10-boot | check-size 17408k
  DEVICE_PACKAGES := kmod-rtw88-8723ds wpad-basic-mbedtls kmod-fs-ext4 e2fsprogs bluez-daemon bluez-utils bluez-utils-extra dbus alsa-utils cmcc-lotus-hf-m10-bluealsa cmcc-lotus-hf-m10-base kmod-cmcc-lotus-hf-m10-audio kmod-hci-uart kmod-cmcc-lotus-hf-m10-keys cmcc-lotus-hf-m10-tools kmod-cmcc-lotus-hf-m10-battery cmcc-lotus-hf-m10-console cmcc-lotus-hf-m10-direct-root dropbear luci uhttpd rpcd
  DEVICE_PACKAGES += -kmod-gpio-button-hotplug -uboot-envtools -partx-utils -mkf2fs
endef
TARGET_DEVICES += cmcc-lotus-hf-m10
