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
	check-syntax \
	run-tests \
	$(NULL)

EXTRA_DIST = \
	$(TESTS) \
	__init__.py \
	test_image_boot.py \
	test_live_storage.py \
	test_migrate_chromium_profile.py \
	test_migrate_firefox_profile.py \
	test_repartition.py \
	test_repartition_mbr.py \
	test_update_flatpak_repos.py \
	util.py \
	$(NULL)
