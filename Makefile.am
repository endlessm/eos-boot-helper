SUBDIRS = dracut

if ENABLE_SYSTEMD
systemdunitdir=/lib/systemd/system
dist_systemdunit_DATA = \
	eos-firstboot.service \
	eos-extra-resize.service \
	endless.mount \
	$(NULL)

# Unfortunately, dist chokes on the escaped \x2d, so we need to
# split this out into EXTRA_DIST unescaped.
systemdunit_DATA = var-endless\\x2dextra.mount
endif

# Needs to be outside systemd conditional or it won't be included.
EXTRA_DIST = var-endless\x2dextra.mount

dist_sbin_SCRIPTS = eos-firstboot eos-extra-resize
