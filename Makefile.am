SUBDIRS = dracut factory-reset flatpak-repos nvidia psi-monitor tests
EXTRA_DIST = debian .flake8

# Install systemd units, generators, preset files, and udev rules
# under $prefix for distcheck
AM_DISTCHECK_CONFIGURE_FLAGS = \
	--with-systemdunitdir='$${prefix}/lib/systemd/system' \
	--with-systemdgeneratordir='$${prefix}/lib/systemd/system-generators' \
	--with-systemdpresetdir='$${prefix}/lib/systemd/system-preset' \
	--with-udevdir='$${prefix}/lib/udev' \
	--with-modprobedir='$${prefix}/lib/modprobe.d' \
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
	$(NULL)

dist_systemdgenerator_SCRIPTS = \
	eos-extra-target-generator \
	eos-live-boot-generator \
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

tmpfilesdir = $(prefix)/lib/tmpfiles.d
dist_tmpfiles_DATA = \
	tmpfiles.d/avahi-service-writers.conf \
	tmpfiles.d/eos-boot-helper.conf \
	$(NULL)
