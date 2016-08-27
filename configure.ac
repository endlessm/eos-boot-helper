AC_INIT([eos-boot-helper], [0.0])

AM_INIT_AUTOMAKE([foreign])
AC_CONFIG_SRCDIR([eos-firstboot])

AC_ARG_ENABLE([systemd],
	AS_HELP_STRING([--enable-systemd],
		[Enable systemd integration]),
	enable_systemd=$enableval, enable_systemd=no)
AM_CONDITIONAL(ENABLE_SYSTEMD, [test "$enable_systemd" = yes])

AC_CONFIG_FILES([
	Makefile
	dracut/Makefile
	dracut/image-boot/Makefile
	dracut/repartition/Makefile])
AC_OUTPUT
