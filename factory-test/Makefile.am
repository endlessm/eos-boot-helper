sbin_PROGRAMS = eos-factory-test-helper
eos_factory_test_helper_SOURCES = helper.c
eos_factory_test_helper_LDADD = $(GLIB_LIBS) $(UDISKS_LIBS)
eos_factory_test_helper_CFLAGS = $(GLIB_CFLAGS) $(UDISKS_CFLAGS)

if ENABLE_SYSTEMD
systemdunitdir=/lib/systemd/system
dist_systemdunit_DATA = eos-factory-test-helper.service \
	eos-factory-test.service \
	eos-factory-test.target
endif
