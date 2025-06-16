SUBDIRS = dracut factory-reset fallback-fb-setup flatpak-repos journald nvidia psi-monitor record-boot-success . tests
EXTRA_DIST = debian .flake8 pytest.ini
CLEANFILES =

AM_CFLAGS = -Wall -Werror

# Install systemd units, generators, preset files, and udev rules
# under $prefix for distcheck
AM_DISTCHECK_CONFIGURE_FLAGS = \
	--with-systemdutildir='$${prefix}/lib/systemd' \
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
	eos-fix-flatpak-overrides.service \
	eos-live-boot-overlayfs-setup.service \
	eos-transient-setup.service \
	eos-update-flatpak-repos.service \
	eos-update-system-ca.service \
	$(NULL)

dist_systemduserunit_DATA = \
	eos-migrate-chromium-profile.service \
	eos-migrate-firefox-profile.service \
	eos-migrate-shotwell.service \
	$(NULL)

dist_systemdgenerator_SCRIPTS = \
	eos-esp-generator \
	eos-live-boot-generator \
	eos-vm-generator \
	$(NULL)

dist_systemdpreset_DATA = \
	50-eos.preset \
	$(NULL)

dist_systemdsystemmanagerconf_DATA = \
	10-eos-oom-policy.conf \
	$(NULL)

dist_systemdusermanagerconf_DATA = \
	10-eos-oom-policy.conf \
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
	50-usb-mouse-wakeup.rules \
	60-suspend-mode.rules \
	$(NULL)

dist_sbin_SCRIPTS = \
	eos-config-journal \
	eos-enable-zram \
	eos-firewall-localonly \
	eos-firstboot \
	eos-live-boot-overlayfs-setup \
	eos-repartition-mbr \
	eos-test-mode \
	eos-transient-setup \
	eos-update-flatpak-repos \
	$(NULL)

sbin_PROGRAMS = \
	eos-update-efi-uuid \
	$(NULL)

eos_update_efi_uuid_SOURCES = eos-update-efi-uuid.c
eos_update_efi_uuid_CFLAGS = $(AM_CFLAGS) $(EFIBOOT_CFLAGS)
eos_update_efi_uuid_LDADD = $(EFIBOOT_LIBS)

dist_libexec_SCRIPTS = \
	eos-migrate-chromium-profile \
	eos-migrate-firefox-profile \
	$(NULL)

tmpfilesdir = $(prefix)/lib/tmpfiles.d
dist_tmpfiles_DATA = \
	tmpfiles.d/chromium-system-services.conf \
	tmpfiles.d/eos-boot-helper.conf \
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
