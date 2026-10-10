include $(TOPDIR)/rules.mk
PKG_NAME:=cmcc-lotus-hf-m10-audio
PKG_VERSION:=1
PKG_RELEASE:=1
include $(INCLUDE_DIR)/kernel.mk
include $(INCLUDE_DIR)/package.mk

define KernelPackage/cmcc-lotus-hf-m10-audio
  SUBMENU:=Sound Support
  TITLE:=CMCC HF-M10 RK3308 B-revision audio
  DEPENDS:=@TARGET_rockchip +kmod-sound-soc-core
  KCONFIG:= \
	CONFIG_SND_SOC_ROCKCHIP \
	CONFIG_SND_SOC_ROCKCHIP_I2S_TDM \
	CONFIG_SND_SOC_LOTUS_RK3308_VENDOR \
	CONFIG_SND_SOC_RK3308=n \
	CONFIG_SND_SIMPLE_CARD_UTILS \
	CONFIG_SND_SIMPLE_CARD
  FILES:= \
	$(LINUX_DIR)/sound/soc/rockchip/snd-soc-rockchip-i2s-tdm.ko \
	$(LINUX_DIR)/sound/soc/codecs/snd-soc-rk3308-lotus-vendor.ko \
	$(LINUX_DIR)/sound/soc/generic/snd-soc-simple-card-utils.ko \
	$(LINUX_DIR)/sound/soc/generic/snd-soc-simple-card.ko
  AUTOLOAD:=$(call AutoProbe,snd-soc-rockchip-i2s-tdm snd-soc-rk3308-lotus-vendor snd-soc-simple-card-utils snd-soc-simple-card)
endef

define KernelPackage/cmcc-lotus-hf-m10-audio/description
  Board audio modules built together with the OpenWrt kernel.
  Requires Lotus device tree and imported codec source; not generic RK3308 firmware.
endef

define Build/Prepare
	$(INSTALL_DIR) $(PKG_BUILD_DIR)
endef

define Build/Configure
endef

define Build/Compile
endef

$(eval $(call KernelPackage,cmcc-lotus-hf-m10-audio))
