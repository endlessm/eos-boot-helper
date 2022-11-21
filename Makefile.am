SUBDIRS = dracut factory-reset fallback-fb-setup flatpak-repos nvidia record-boot-success tests
EXTRA_DIST = debian .flake8
CLEANFILES =

# Install systemd units, generators, preset files, and udev rules
# under $prefix for distcheck
AM_DISTCHECK_CONFIGURE_FLAGS = \
	--with-systemdunitdir='$${prefix}/lib/systemd/system' \
	--with-systemduserunitdir='$${prefix}/lib/systemd/user' \
	--with-systemdgeneratordir='$${prefix}/lib/systemd/system-generators' \
	--with-systemdpresetdir='$${prefix}/lib/systemd/system-preset' \
	--with-udevdir='$${prefix}/lib/udev' \
	--with-modprobedir='$${prefix}/lib/modprobe.d' \
	--with-dbussystemconfigdir='$${prefix}/share/dbus-1/system.d' \
	--with-system-bus-services-dir='$${prefix}/share/dbus-1/system-services' \
	--with-polkitpolicydir='$${prefix}/share/polkit-1/actions' \
	$(NULL)

dist_systemdunit_DATA = \
	eos-config-journal.service \
	eos-enable-zram.service \
	eos-firewall-localonly.service \
	eos-firstboot.service \
	eos-image-boot-dm-setup.service \
	eos-live-boot-overlayfs-setup.service \
	eos-ostree-bootloader-setup.service \
	eos-prune-printers.service \
	eos-split-flatpak-repo.service \
	eos-transient-setup.service \
	eos-update-flatpak-repos.service \
	hack-remove-global-override.service \
	$(NULL)

dist_systemduserunit_DATA = \
	eos-migrate-chromium-profile.service \
	eos-migrate-firefox-profile.service \
	eos-migrate-shotwell.service \
	$(NULL)

dist_systemdgenerator_SCRIPTS = \
	eos-live-boot-generator \
	eos-vm-generator \
	$(NULL)

dist_systemdpreset_DATA = \
	50-eos.preset \
	$(NULL)

# Network Manager dispatcher script for the firewall - scripts which
# are a symlink to no-wait.d will be run without blocking/ordering.
# install the script here and make the symlink in install-data-hook
# below
networkscriptdir = $(sysconfdir)/NetworkManager/dispatcher.d
networkscriptnowaitdir = $(networkscriptdir)/no-wait.d
dist_networkscriptnowait_DATA = eos-firewall-localonly-nm

install-data-hook:
	$(MKDIR_P) '$(DESTDIR)$(networkscriptdir)'
	ln -s 'no-wait.d/eos-firewall-localonly-nm' \
	  '$(DESTDIR)$(networkscriptdir)/eos-firewall-localonly-nm'
	chmod +x '$(DESTDIR)$(networkscriptdir)/eos-firewall-localonly-nm'
	$(MKDIR_P) '$(DESTDIR)$(systemduserunitdir)/gnome-session.target.wants'
	ln -s ../eos-migrate-chromium-profile.service '$(DESTDIR)$(systemduserunitdir)/gnome-session.target.wants'
	ln -s ../eos-migrate-firefox-profile.service '$(DESTDIR)$(systemduserunitdir)/gnome-session.target.wants'
	ln -s ../eos-migrate-shotwell.service '$(DESTDIR)$(systemduserunitdir)/gnome-session.target.wants'

uninstall-hook:
	rm -f '$(DESTDIR)$(networkscriptdir)/eos-firewall-localonly-nm'

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
	eos-firewall-localonly \
	eos-firstboot \
	eos-image-boot-dm-setup \
	eos-live-boot-overlayfs-setup \
	eos-ostree-bootloader-setup \
	eos-prune-printers \
	eos-repartition-mbr \
	eos-split-flatpak-repo \
	eos-test-mode \
	eos-transient-setup \
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
	tmpfiles.d/chromium-system-services.conf \
	tmpfiles.d/eos-boot-helper.conf \
	tmpfiles.d/flatpak-overrides.conf \
	$(NULL)

com.endlessm.TestMode.policy: com.endlessm.TestMode.policy.in
	$(AM_V_GEN) $(SED) -e 's|[@]sbindir@|$(sbindir)|g' < "$<" > "$@"

polkitpolicy_DATA = \
	com.endlessm.TestMode.policy \
	$(NULL)

CLEANFILES += \
	com.endlessm.TestMode.policy
EXTRA_DIST += \
	com.endlessm.TestMode.policy.in
