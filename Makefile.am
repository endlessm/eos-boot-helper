SUBDIRS = dracut

if ENABLE_SYSTEMD
systemdunitdir=/lib/systemd/system
dist_systemdunit_DATA = eos-firstboot.service eos-extra-resize.service
endif

dist_sbin_SCRIPTS = eos-firstboot eos-extra-resize
