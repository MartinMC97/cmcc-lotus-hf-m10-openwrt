include $(TOPDIR)/rules.mk
PKG_NAME:=cmcc-lotus-hf-m10-keys
PKG_VERSION:=1
PKG_RELEASE:=1
include $(INCLUDE_DIR)/kernel.mk
include $(INCLUDE_DIR)/package.mk

define KernelPackage/cmcc-lotus-hf-m10-keys
  SUBMENU:=Input modules
  TITLE:=CMCC HF-M10 ADC and GPIO keys
  DEPENDS:=@TARGET_rockchip +kmod-input-gpio-keys +kmod-input-evdev +kmod-iio-core +kmod-industrialio-triggered-buffer
  KCONFIG:=CONFIG_KEYBOARD_ADC CONFIG_ROCKCHIP_SARADC
  FILES:= \
	$(LINUX_DIR)/drivers/input/keyboard/adc-keys.ko \
	$(LINUX_DIR)/drivers/iio/adc/rockchip_saradc.ko
  AUTOLOAD:=$(call AutoProbe,rockchip_saradc adc-keys)
endef

define Build/Prepare
	$(INSTALL_DIR) $(PKG_BUILD_DIR)
endef

define Build/Configure
endef

define Build/Compile
endef

$(eval $(call KernelPackage,cmcc-lotus-hf-m10-keys))
