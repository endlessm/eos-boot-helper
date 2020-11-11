SUBDIRS = dracut factory-reset fallback-fb-setup flatpak-repos nvidia psi-monitor record-boot-success tests
EXTRA_DIST = debian .flake8

# Install systemd units, generators, preset files, and udev rules
# under $prefix for distcheck
AM_DISTCHECK_CONFIGURE_FLAGS = \
	--with-systemdunitdir='$${prefix}/lib/systemd/system' \
	--with-systemduserunitdir='$${prefix}/lib/systemd/user' \
	--with-systemdgeneratordir='$${prefix}/lib/systemd/system-generators' \
	--with-systemdpresetdir='$${prefix}/lib/systemd/system-preset' \
	--with-systemduserpresetdir='$${prefix}/lib/systemd/user-preset' \
	--with-udevdir='$${prefix}/lib/udev' \
	--with-modprobedir='$${prefix}/lib/modprobe.d' \
	--with-dbussystemconfigdir='$${prefix}/share/dbus-1/system.d' \
	--with-system-bus-services-dir='$${prefix}/share/dbus-1/system-services' \
	$(NULL)

dist_systemdunit_DATA = \
	eos-config-journal.service \
	eos-enable-zram.service \
	eos-extra-resize.service \
	eos-firewall-localonly.service \
	eos-firstboot.service \
	eos-image-boot-dm-setup.service \
	eos-live-boot-overlayfs-setup.service \
	eos-reclaim-swap.service \
	eos-update-flatpak-repos.service \
	hack-remove-global-override.service \
	$(NULL)

dist_systemduserunit_DATA = \
	eos-migrate-chromium-profile.service \
	eos-migrate-firefox-profile.service \
	$(NULL)

dist_systemdgenerator_SCRIPTS = \
	eos-extra-target-generator \
	eos-live-boot-generator \
	$(NULL)

dist_systemdpreset_DATA = \
	50-eos.preset \
	$(NULL)

dist_systemduserpreset_DATA = \
	50-eos-user.preset \
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
	$(MKDIR_P) '$(DESTDIR)$(systemduserunitdir)/gnome-session.target.wants'
	ln -s ../eos-migrate-chromium-profile.service '$(DESTDIR)$(systemduserunitdir)/gnome-session.target.wants'
	ln -s ../eos-migrate-firefox-profile.service '$(DESTDIR)$(systemduserunitdir)/gnome-session.target.wants'

uninstall-hook:
	rm -f '$(DESTDIR)$(networkscriptdir)/eos-firewall-localonly-nm'
	rm -f '$(DESTDIR)$(systemdunitdir)/var-endless\x2dextra.mount'

udevrulesdir = $(udevdir)/rules.d
dist_udevrules_DATA = \
	50-disk-bfq.rules \
	50-meson-vdec.rules \
	50-usb-mouse-wakeup.rules \
	$(NULL)

polkitrulesdir = $(datadir)/polkit-1/rules.d
dist_polkitrules_DATA = \
	10-allow-mounting-endless-image-device.rules \
	$(NULL)

dist_sbin_SCRIPTS = \
	eos-config-journal \
	eos-enable-zram \
	eos-extra-resize \
	eos-firewall-localonly \
	eos-firstboot \
	eos-image-boot-dm-setup \
	eos-live-boot-overlayfs-setup \
	eos-reclaim-swap \
	eos-repartition-mbr \
	eos-update-flatpak-repos \
	$(NULL)

dist_libexec_SCRIPTS = \
	dracut/image-boot/eos-map-image-file \
	eos-migrate-chromium-profile \
	eos-migrate-firefox-profile \
	$(NULL)

tmpfilesdir = $(prefix)/lib/tmpfiles.d
dist_tmpfiles_DATA = \
	tmpfiles.d/avahi-service-writers.conf \
	tmpfiles.d/eos-boot-helper.conf \
	tmpfiles.d/flatpak-overrides.conf \
	$(NULL)

extratmpfilesdir = $(pkgdatadir)/tmpfiles.d
dist_extratmpfiles_DATA = \
	tmpfiles.d/flatpak-extension-kiwix-usb-content.conf \
	$(NULL)

