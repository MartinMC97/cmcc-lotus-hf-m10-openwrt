include $(TOPDIR)/rules.mk

PKG_NAME:=cmcc-lotus-hf-m10-tools
PKG_VERSION:=1
PKG_RELEASE:=1
PKG_LICENSE:=MIT

include $(INCLUDE_DIR)/package.mk

define Package/cmcc-lotus-hf-m10-tools
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=CMCC HF-M10 bounded hardware diagnostics
  DEPENDS:=@TARGET_rockchip_hf_m10
endef

define Build/Prepare
	$(INSTALL_DIR) $(PKG_BUILD_DIR)
	$(CP) ./src/lotus-led-breathe.c $(PKG_BUILD_DIR)/
endef

define Build/Compile
	$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) \
		-o $(PKG_BUILD_DIR)/lotus-led-breathe $(PKG_BUILD_DIR)/lotus-led-breathe.c $(TARGET_LDFLAGS)
endef

define Package/cmcc-lotus-hf-m10-tools/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/lotus-led-breathe $(1)/usr/bin/
endef

$(eval $(call BuildPackage,cmcc-lotus-hf-m10-tools))
