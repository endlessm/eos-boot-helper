AM_TESTS_ENVIRONMENT = \
	BUILDDIR='$(builddir)' \
	TOP_BUILDDIR='$(top_builddir)' \
	ABS_BUILDDIR='$(abs_builddir)' \
	ABS_TOP_BUILDDIR='$(abs_top_builddir)' \
	SRCDIR='$(srcdir)' \
	TOP_SRCDIR='$(top_srcdir)' \
	ABS_SRCDIR='$(abs_srcdir)' \
	ABS_TOP_SRCDIR='$(abs_top_srcdir)' \
	$(NULL)

TESTS = \
	check-syntax.tap \
	run-tests \
	$(NULL)

TEST_EXTENSIONS = .tap
TAP_LOG_DRIVER = env AM_TAP_AWK='$(AWK)' $(SHELL) $(top_srcdir)/build-aux/tap-driver.sh

EXTRA_DIST = \
	$(TESTS) \
	__init__.py \
	conftest.py \
	efivars \
	espgen \
	test_esp_generator.py \
	test_image_boot.py \
	test_live_storage.py \
	test_migrate_chrome_profile.py \
	test_migrate_chromium_profile.py \
	test_migrate_firefox_profile.py \
	test_repartition.py \
	test_repartition_mbr.py \
	test_update_efi_uuid.py \
	test_update_flatpak_repos.py \
	util.py \
	$(NULL)
