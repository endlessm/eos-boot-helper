SUBDIRS = dracut
EXTRA_DIST = debian

if ENABLE_SYSTEMD
systemdunitdir=/lib/systemd/system
dist_systemdunit_DATA = \
	eos-firstboot.service \
	eos-extra-resize.service \
	eos-enable-extra-upgrade.service \
	eos-enable-zram.service \
	eos-setgoodroot.service \
	$(NULL)

# Unfortunately, dist chokes on the escaped \x2d, so we need to
# split this out into EXTRA_DIST unescaped.
systemdunit_DATA = \
	dev-disk-by\\x2dlabel-eos\\x2dswap.swap \
	var-endless\\x2dextra.mount

udevrulesdir=/lib/udev/rules.d
dist_udevrules_DATA = 50-meson-vdec.rules

dbussystemservicedir=/usr/share/dbus-1/system-services
dist_dbussystemservice_DATA = com.endlessm.SetGoodRoot.service
endif

# Needs to be outside systemd conditional or it won't be included.
EXTRA_DIST += \
	dev-disk-by\x2dlabel-eos\x2dswap.swap \
	var-endless\x2dextra.mount

dist_sbin_SCRIPTS = \
	eos-firstboot \
	eos-extra-resize \
	eos-enable-extra-upgrade \
	eos-enable-zram \
	eos-setgoodroot \
	$(NULL)

autostartdir = $(sysconfdir)/xdg/autostart
dist_autostart_DATA = com.endlessm.SetGoodRoot.desktop
