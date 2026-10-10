include $(TOPDIR)/rules.mk
PKG_NAME:=hf-m10-resource
PKG_VERSION:=1
PKG_RELEASE:=1
PKG_LICENSE:=GPL-2.0-or-later
include $(INCLUDE_DIR)/host-build.mk

define Host/Prepare
	$(INSTALL_DIR) $(HOST_BUILD_DIR)
	$(CP) ./src/resource_tool.c $(HOST_BUILD_DIR)/
endef

define Host/Configure
endef

define Host/Compile
	$(HOSTCC) $(HOST_CFLAGS) -o $(HOST_BUILD_DIR)/hf-m10-resource-tool $(HOST_BUILD_DIR)/resource_tool.c $(HOST_LDFLAGS)
endef

define Host/Install
	$(INSTALL_BIN) $(HOST_BUILD_DIR)/hf-m10-resource-tool $(STAGING_DIR_HOST)/bin/
endef

define Host/Clean
	rm -f $(STAGING_DIR_HOST)/bin/hf-m10-resource-tool
endef

$(eval $(call HostBuild))
