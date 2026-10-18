include $(TOPDIR)/rules.mk

PKG_NAME:=cmcc-lotus-hf-m10-base
PKG_VERSION:=1
PKG_RELEASE:=8

include $(INCLUDE_DIR)/package.mk

define Package/cmcc-lotus-hf-m10-base
  SECTION:=base
  CATEGORY:=Base system
  TITLE:=CMCC HF-M10 board defaults (staging)
  DEPENDS:=+uci +ubus +jsonfilter
endef

define Package/cmcc-lotus-hf-m10-base/description
  Credential-free board defaults and NTP DHCP resolver rebinding.
  Does not supply kernel drivers, bootstrap, wireless identity or flash support.
endef

define Package/cmcc-lotus-hf-m10-base/conffiles
/etc/sysctl.d/99-lotus-memory.conf
endef

define Build/Compile
endef

define Package/cmcc-lotus-hf-m10-base/install
	$(INSTALL_DIR) $(1)/lib/preinit
	$(INSTALL_DATA) ./files/lotus-partitions $(1)/lib/lotus-partitions.sh
	$(INSTALL_DATA) ./files/69_lotus_premounted $(1)/lib/preinit/
	$(INSTALL_DIR) $(1)/etc/uci-defaults $(1)/etc/hotplug.d/iface
	$(INSTALL_BIN) ./files/98-cmcc-lotus-hf-m10-wifi-compat $(1)/etc/uci-defaults/
	$(INSTALL_BIN) ./files/99-cmcc-lotus-hf-m10 $(1)/etc/uci-defaults/
	$(INSTALL_BIN) ./files/91-lotus-ntp $(1)/etc/hotplug.d/iface/
	$(INSTALL_DIR) $(1)/etc/sysctl.d
	$(INSTALL_DATA) ./files/99-lotus-memory.conf $(1)/etc/sysctl.d/
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) ./files/lotus-health $(1)/usr/bin/
	$(INSTALL_BIN) ./files/lotus-sensors $(1)/usr/bin/
	$(INSTALL_BIN) ./files/lotus-thermal-check $(1)/usr/bin/
	$(INSTALL_DIR) $(1)/usr/share/luci/menu.d $(1)/usr/share/rpcd/acl.d
	$(INSTALL_DATA) ./files/lotus-sensors-menu.json $(1)/usr/share/luci/menu.d/lotus-sensors.json
	$(INSTALL_DATA) ./files/lotus-sensors-acl.json $(1)/usr/share/rpcd/acl.d/lotus-sensors.json
	$(INSTALL_DIR) $(1)/www/luci-static/resources/view/status
	$(INSTALL_DATA) ./files/lotus_sensors.js $(1)/www/luci-static/resources/view/status/
endef

$(eval $(call BuildPackage,cmcc-lotus-hf-m10-base))
