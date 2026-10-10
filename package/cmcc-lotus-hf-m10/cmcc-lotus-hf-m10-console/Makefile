include $(TOPDIR)/rules.mk
PKG_NAME:=cmcc-lotus-hf-m10-console
PKG_VERSION:=1.37.0
PKG_RELEASE:=5
PKG_SOURCE:=busybox-$(PKG_VERSION).tar.bz2
PKG_SOURCE_URL:=https://www.busybox.net/downloads
PKG_HASH:=3311dff32e746499f4df0d5df04d7eb396382d7e108bb9250e7b519b837043a4
PKG_BUILD_DIR:=$(BUILD_DIR)/cmcc-hf-m10-console-busybox-$(PKG_VERSION)
PKG_LICENSE:=GPL-2.0
PKG_LICENSE_FILES:=LICENSE
PKG_BUILD_PARALLEL:=1
include $(INCLUDE_DIR)/package.mk

define Package/cmcc-lotus-hf-m10-console
  SECTION:=base
  CATEGORY:=Base system
  TITLE:=CMCC HF-M10 authenticated USB serial console (candidate)
  DEPENDS:=+busybox
endef

define Package/cmcc-lotus-hf-m10-direct-root
  SECTION:=base
  CATEGORY:=Base system
  TITLE:=CMCC HF-M10 premounted switch_root hook (candidate)
  DEPENDS:=+cmcc-lotus-hf-m10-console +cmcc-lotus-hf-m10-base
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(TAR) -C $(PKG_BUILD_DIR) --strip-components=1 -xf $(DL_DIR)/$(PKG_SOURCE)
endef

define Build/Configure
	$(MAKE) -C $(PKG_BUILD_DIR) allnoconfig
	python3 ./configure-busybox.py $(PKG_BUILD_DIR) ./busybox.config
endef

define Build/Compile
	$(MAKE) -C $(PKG_BUILD_DIR) $(MAKE_FLAGS) CROSS_COMPILE="$(TARGET_CROSS)" EXTRA_CFLAGS="$(TARGET_CFLAGS)"
endef

define Package/cmcc-lotus-hf-m10-console/install
	$(INSTALL_DIR) $(1)/usr/libexec $(1)/etc/init.d
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/busybox $(1)/usr/libexec/busybox-hf-m10
	$(INSTALL_BIN) ./files/lotus-usb-gadget $(1)/usr/libexec/
	$(INSTALL_BIN) ./files/lotus-console-login $(1)/usr/libexec/
	$(INSTALL_BIN) ./files/lotus-console $(1)/etc/init.d/
endef

define Package/cmcc-lotus-hf-m10-direct-root/install
	$(INSTALL_DIR) $(1)/lib/preinit $(1)/lib/lotus
	sed '/^boot_hook_add /d' ./files/69_lotus_premounted > $(1)/lib/preinit/79_lotus_switch_root
	$(INSTALL_DATA) ./files/bootstrap/lotus-partitions $(1)/lib/lotus/partitions.sh
endef
$(eval $(call BuildPackage,cmcc-lotus-hf-m10-console))
$(eval $(call BuildPackage,cmcc-lotus-hf-m10-direct-root))
