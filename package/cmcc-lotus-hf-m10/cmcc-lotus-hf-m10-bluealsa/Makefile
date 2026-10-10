include $(TOPDIR)/rules.mk

PKG_NAME:=cmcc-lotus-hf-m10-bluealsa
PKG_VERSION:=4.0.0
PKG_RELEASE:=1
PKG_SOURCE:=bluez-alsa-$(PKG_VERSION).tar.gz
PKG_SOURCE_URL:=https://github.com/arkq/bluez-alsa/archive/refs/tags/
PKG_SOURCE_URL_FILE:=v$(PKG_VERSION).tar.gz
PKG_HASH:=ce5e060e61669d61d44f5f9bad34a7b88378376e9d49d31482406a68127a6b29
PKG_BUILD_DIR:=$(BUILD_DIR)/bluez-alsa-$(PKG_VERSION)
PKG_LICENSE:=MIT
PKG_LICENSE_FILES:=LICENSE
PKG_FIXUP:=autoreconf
PKG_INSTALL:=1
PKG_BUILD_PARALLEL:=1

include $(INCLUDE_DIR)/package.mk

define Package/cmcc-lotus-hf-m10-bluealsa
  SECTION:=sound
  CATEGORY:=Sound
  TITLE:=CMCC HF-M10 native BlueALSA SBC sink
  URL:=https://github.com/arkq/bluez-alsa
  DEPENDS:=+alsa-lib +bluez-libs +bluez-daemon +dbus +glib2 +sbc +libpthread +librt
endef

define Package/cmcc-lotus-hf-m10-bluealsa/description
  Native musl BlueALSA daemon and ALSA playback client. SBC only.
  The Lotus playback service is disabled by default; no pairing agent,
  discovery, trusted peer or credentials are installed automatically.
endef

define Package/cmcc-lotus-hf-m10-bluealsa/conffiles
/etc/config/lotus_bluealsa
/etc/lotus-bt-asound.conf
endef

CONFIGURE_ARGS += \
  --disable-static --enable-shared --disable-debug \
  --enable-aplay --enable-cli --disable-rfcomm --disable-hcitop \
  --disable-manpages --disable-test --disable-systemd \
  --disable-aac --disable-aptx --disable-aptx-hd --disable-faststream \
  --disable-lc3plus --disable-ldac --disable-mp3lame --disable-mpg123 \
  --disable-msbc --disable-ofono --disable-upower \
  --without-bash-completion --with-alsaplugindir=/usr/lib/alsa-lib \
  --with-alsaconfdir=/usr/share/alsa/alsa.conf.d \
  --with-dbusconfdir=/etc/dbus-1/system.d

define Package/cmcc-lotus-hf-m10-bluealsa/install
	$(INSTALL_DIR) $(1)/usr/bin $(1)/usr/lib/alsa-lib $(1)/usr/share/alsa/alsa.conf.d
	$(INSTALL_BIN) $(PKG_INSTALL_DIR)/usr/bin/bluealsa $(1)/usr/bin/
	$(INSTALL_BIN) $(PKG_INSTALL_DIR)/usr/bin/bluealsa-aplay $(1)/usr/bin/
	$(INSTALL_BIN) $(PKG_INSTALL_DIR)/usr/bin/bluealsa-cli $(1)/usr/bin/
	$(CP) $(PKG_INSTALL_DIR)/usr/lib/alsa-lib/*.so $(1)/usr/lib/alsa-lib/
	$(INSTALL_DATA) $(PKG_INSTALL_DIR)/usr/share/alsa/alsa.conf.d/* $(1)/usr/share/alsa/alsa.conf.d/
	$(INSTALL_DIR) $(1)/etc/dbus-1/system.d $(1)/etc/init.d $(1)/etc/config
	$(INSTALL_DATA) $(PKG_INSTALL_DIR)/etc/dbus-1/system.d/* $(1)/etc/dbus-1/system.d/
	$(INSTALL_BIN) ./files/bluealsa.init $(1)/etc/init.d/lotus-bluealsa
	$(INSTALL_DATA) ./files/lotus_bluealsa.config $(1)/etc/config/lotus_bluealsa
	$(INSTALL_DATA) ./files/lotus-bt-asound.conf $(1)/etc/lotus-bt-asound.conf
endef

$(eval $(call BuildPackage,cmcc-lotus-hf-m10-bluealsa))
