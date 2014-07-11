AC_INIT([eos-boot-helper], [0.0])

AM_INIT_AUTOMAKE([foreign])
AM_SILENT_RULES([yes])
AC_CONFIG_SRCDIR([eos-firstboot])

AM_PROG_CC_C_O
PKG_CHECK_MODULES([GLIB], [glib-2.0])
PKG_CHECK_MODULES([UDISKS], [udisks2])

AC_CONFIG_FILES([
	Makefile
	dracut/Makefile
	dracut/repartition/Makefile
	factory-test/Makefile])
AC_OUTPUT
