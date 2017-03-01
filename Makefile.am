SUBDIRS = dracut
EXTRA_DIST = debian

# Install systemd units and udev rules under $prefix for distcheck
AM_DISTCHECK_CONFIGURE_FLAGS = \
	--with-systemdunitdir='$${prefix}/lib/systemd/systemd' \
	--with-udevdir='$${prefix}/lib/udev' \
	$(NULL)

dist_systemdunit_DATA = \
	eos-add-flatpak-gnome-repos.service \
	eos-enable-extra-upgrade.service \
	eos-enable-zram.service \
	eos-extra-resize.service \
	eos-firstboot.service \
	eos-fix-flatpak-branches.service \
	eos-image-boot-dm-setup.service \
	eos-live-boot-overlayfs-setup.service \
	$(NULL)

# Unfortunately, the escaped \x2d is handled poorly, so we distribute
# this unit under another name and install it by hand.
EXTRA_DIST += \
	var-endless_x2dextra.mount

install-data-hook:
	$(MKDIR_P) '$(DESTDIR)$(systemdunitdir)'
	$(INSTALL_DATA) $(srcdir)/var-endless_x2dextra.mount \
	  '$(DESTDIR)$(systemdunitdir)/var-endless\x2dextra.mount'

uninstall-hook:
	rm -f '$(DESTDIR)$(systemdunitdir)/var-endless\x2dextra.mount'

udevrulesdir = $(udevdir)/rules.d
dist_udevrules_DATA = 50-meson-vdec.rules

polkitrulesdir = $(datadir)/polkit-1/rules.d
dist_polkitrules_DATA = \
	10-allow-mounting-endless-image-device.rules \
	$(NULL)

dist_sbin_SCRIPTS = \
	eos-add-flatpak-gnome-repos \
	eos-enable-extra-upgrade \
	eos-enable-zram \
	eos-extra-resize \
	eos-firstboot \
	eos-fix-flatpak-branches \
	eos-image-boot-dm-setup \
	eos-live-boot-overlayfs-setup \
	eos-repartition-mbr \
	$(NULL)
