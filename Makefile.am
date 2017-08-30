SUBDIRS = dracut tests
EXTRA_DIST = debian

# Install systemd units and generators and udev rules under $prefix for distcheck
AM_DISTCHECK_CONFIGURE_FLAGS = \
	--with-systemdunitdir='$${prefix}/lib/systemd/system' \
	--with-systemdgeneratordir='$${prefix}/lib/systemd/system-generators' \
	--with-udevdir='$${prefix}/lib/udev' \
	$(NULL)

dist_systemdunit_DATA = \
	boot.mount \
	eos-add-flatpak-apps-repos.service \
	eos-add-flatpak-flathub-repos.service \
	eos-add-flatpak-gnome-repos.service \
	eos-enable-extra-upgrade.service \
	eos-enable-zram.service \
	eos-extra-resize.service \
	eos-firewall-localonly.service \
	eos-firstboot.service \
	eos-fix-flatpak-branches.service \
	eos-fix-home-dir-permissions.service \
	eos-image-boot-dm-setup.service \
	eos-live-boot-overlayfs-setup.service \
	eos-migrate-image-defaults.service \
	eos-remove-legacy-external-apps.service \
	$(NULL)

dist_systemdgenerator_SCRIPTS = \
	eos-live-boot-generator \
	$(NULL)

# Network Manager dispatcher script for the firewall - scripts which
# are a symlink to no-wait.d will be run without blocking/ordering.
# install the script here and make the symlink in install-data-hook
# below
networkscriptdir = $(sysconfdir)/NetworkManager/dispatcher.d
networkscriptnowaitdir = $(networkscriptdir)/no-wait.d
dist_networkscriptnowait_DATA = eos-firewall-localonly-nm

# Unfortunately, the escaped \x2d is handled poorly, so we distribute
# this unit under another name and install it by hand.
EXTRA_DIST += \
	var-endless_x2dextra.mount

install-data-hook:
	$(MKDIR_P) '$(DESTDIR)$(networkscriptdir)'
	ln -s 'no-wait.d/eos-firewall-localonly-nm' \
	  '$(DESTDIR)$(networkscriptdir)/eos-firewall-localonly-nm'
	chmod +x '$(DESTDIR)$(networkscriptdir)/eos-firewall-localonly-nm'
	$(MKDIR_P) '$(DESTDIR)$(systemdunitdir)'
	$(INSTALL_DATA) $(srcdir)/var-endless_x2dextra.mount \
	  '$(DESTDIR)$(systemdunitdir)/var-endless\x2dextra.mount'

uninstall-hook:
	rm -f '$(DESTDIR)$(networkscriptdir)/eos-firewall-localonly-nm'
	rm -f '$(DESTDIR)$(systemdunitdir)/var-endless\x2dextra.mount'

udevrulesdir = $(udevdir)/rules.d
dist_udevrules_DATA = 50-meson-vdec.rules

polkitrulesdir = $(datadir)/polkit-1/rules.d
dist_polkitrules_DATA = \
	10-allow-mounting-endless-image-device.rules \
	$(NULL)

dist_sbin_SCRIPTS = \
	eos-add-flatpak-apps-repos \
	eos-add-flatpak-flathub-repos \
	eos-add-flatpak-gnome-repos \
	eos-enable-extra-upgrade \
	eos-enable-zram \
	eos-extra-resize \
	eos-firewall-localonly \
	eos-firstboot \
	eos-fix-flatpak-branches \
	eos-fix-home-dir-permissions \
	eos-image-boot-dm-setup \
	eos-live-boot-overlayfs-setup \
	eos-migrate-image-defaults \
	eos-remove-legacy-external-apps \
	eos-repartition-mbr \
	$(NULL)
