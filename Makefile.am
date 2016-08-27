SUBDIRS = dracut
EXTRA_DIST = debian

if ENABLE_SYSTEMD
systemdunitdir=/lib/systemd/system
dist_systemdunit_DATA = \
	eos-firstboot.service \
	eos-extra-resize.service \
	eos-enable-extra-upgrade.service \
	eos-enable-zram.service \
	eos-live-boot-overlayfs-setup.service \
	$(NULL)

# Unfortunately, the escaped \x2d is handled poorly, so we distribute
# this unit under another name and install it by hand.
install-data-hook:
	$(MKDIR_P) '$(DESTDIR)$(systemdunitdir)'
	$(INSTALL_DATA) $(srcdir)/var-endless_x2dextra.mount \
	  '$(DESTDIR)$(systemdunitdir)/var-endless\x2dextra.mount'

uninstall-hook:
	rm -f '$(DESTDIR)$(systemdunitdir)/var-endless\x2dextra.mount'

udevrulesdir=/lib/udev/rules.d
dist_udevrules_DATA = 50-meson-vdec.rules
endif

# Needs to be outside systemd conditional or it won't be included.
EXTRA_DIST += \
	var-endless_x2dextra.mount

dist_sbin_SCRIPTS = \
	eos-firstboot \
	eos-extra-resize \
	eos-enable-extra-upgrade \
	eos-enable-zram \
	eos-live-boot-overlayfs-setup \
	eos-repartition-mbr \
	$(NULL)
