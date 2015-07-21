SUBDIRS = dracut
EXTRA_DIST = debian

if ENABLE_SYSTEMD
systemdunitdir=/lib/systemd/system
dist_systemdunit_DATA = \
	eos-firstboot.service \
	eos-extra-resize.service \
	boot.mount \
	endless.mount \
	endless-mount-dirs.service \
	eos-enable-extra-upgrade.service \
	$(NULL)

# Unfortunately, dist chokes on the escaped \x2d, so we need to
# split this out into EXTRA_DIST unescaped.
systemdunit_DATA = \
	dev-disk-by\\x2dlabel-eos\\x2dswap.swap \
	var-endless\\x2dextra.mount
endif

# Needs to be outside systemd conditional or it won't be included.
EXTRA_DIST += \
	dev-disk-by\x2dlabel-eos\x2dswap.swap \
	var-endless\x2dextra.mount

dist_sbin_SCRIPTS = \
	eos-firstboot \
	eos-extra-resize \
	eos-enable-extra-upgrade \
	$(NULL)
