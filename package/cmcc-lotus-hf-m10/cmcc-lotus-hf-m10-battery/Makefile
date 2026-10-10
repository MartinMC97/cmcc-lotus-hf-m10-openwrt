include $(TOPDIR)/rules.mk
PKG_NAME:=cmcc-lotus-hf-m10-battery
PKG_VERSION:=1
PKG_RELEASE:=1
PKG_LICENSE:=GPL-2.0-only
include $(INCLUDE_DIR)/kernel.mk
include $(INCLUDE_DIR)/package.mk

define KernelPackage/cmcc-lotus-hf-m10-battery
  SUBMENU:=Other modules
  TITLE:=CMCC HF-M10 read-only five-level battery indicator
  DEPENDS:=@TARGET_rockchip_hf_m10
  KCONFIG:=CONFIG_POWER_SUPPLY=y
  FILES:=$(PKG_BUILD_DIR)/lotus-mini-battery.ko
  AUTOLOAD:=$(call AutoProbe,lotus-mini-battery)
endef

define Build/Prepare
	$(INSTALL_DIR) $(PKG_BUILD_DIR)
	$(CP) ./src/* $(PKG_BUILD_DIR)/
endef

define Build/Compile
	$(KERNEL_MAKE) M="$(PKG_BUILD_DIR)" modules
endef

$(eval $(call KernelPackage,cmcc-lotus-hf-m10-battery))
