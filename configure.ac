AC_INIT([eos-boot-helper], [0.0])

AM_INIT_AUTOMAKE([foreign])
AC_CONFIG_SRCDIR([eos-firstboot])
PKG_PROG_PKG_CONFIG

AC_PROG_CC
AC_CANONICAL_TARGET

dnl Get systemd unit and udev rules directories. Add options so that they
dnl can be set under $prefix for distcheck.
m4_define([no_systemdunitdir_error],
          [m4_normalize([Could not get systemdsystemunitdir setting from]
                        [systemd pkg-config file])])
m4_define([no_systemdsystemgeneratordir_error],
          [m4_normalize([Could not get systemdsystemgeneratordir setting from]
                        [systemd pkg-config file])])
m4_define([no_systemdsystempresetdir_error],
          [m4_normalize([Could not get systemdsystempresetdir setting from]
                        [systemd pkg-config file])])
m4_define([no_systemduserpresetdir_error],
          [m4_normalize([Could not get systemduserpresetdir setting from]
                        [systemd pkg-config file])])
m4_define([no_udev_error],
          [m4_normalize([Could not get udevdir setting from udev]
                        [pkg-config file])])
m4_define([no_systembusservicesdir_error],
          [m4_normalize([Could not get system_bus_services_dir setting from]
                        [dbus pkg-config file])])

AC_ARG_WITH([systemdunitdir],
            [AS_HELP_STRING([--with-systemdunitdir],
                            [Path to the system directory for systemd units])],
            [systemdunitdir="$withval"],
            [PKG_CHECK_VAR([systemdunitdir], [systemd],
                           [systemdsystemunitdir], [],
                           [AC_MSG_ERROR(no_systemdunitdir_error)])])
AC_ARG_WITH([systemduserunitdir],
            [AS_HELP_STRING([--with-systemduserunitdir],
                            [Path to the system directory for systemd user units])],
            [systemduserunitdir="$withval"],
            [PKG_CHECK_VAR([systemduserunitdir], [systemd],
                           [systemduserunitdir], [],
                           [AC_MSG_ERROR(no_systemduserunitdir_error)])])
AC_ARG_WITH([systemdgeneratordir],
            [AS_HELP_STRING([--with-systemdgeneratordir],
                            [Path to the system directory for systemd generators])],
            [systemdgeneratordir="$withval"],
            [PKG_CHECK_VAR([systemdgeneratordir], [systemd],
                           [systemdsystemgeneratordir], [],
                           [AC_MSG_ERROR(no_systemdsystemgeneratordir_error)])])
AC_ARG_WITH([systemdpresetdir],
            [AS_HELP_STRING([--with-systemdpresetdir],
                            [Path to the system directory for systemd presets])],
            [systemdpresetdir="$withval"],
            [PKG_CHECK_VAR([systemdpresetdir], [systemd],
                           [systemdsystempresetdir], [],
                           [AC_MSG_ERROR(no_systemdsystempresetdir_error)])])
AC_ARG_WITH([systemduserpresetdir],
            [AS_HELP_STRING([--with-systemduserpresetdir],
                            [Path to the system directory for systemd user presets])],
            [systemduserpresetdir="$withval"],
            [PKG_CHECK_VAR([systemduserpresetdir], [systemd],
                           [systemduserpresetdir], [],
                           [AC_MSG_ERROR(no_systemduserpresetdir_error)])])
AC_ARG_WITH([udevdir],
            [AS_HELP_STRING([--with-udevdir],
                            [Path to the system udev directory])],
            [udevdir="$withval"],
            [PKG_CHECK_VAR([udevdir], [udev],
                           [udevdir], [],
                           [AC_MSG_ERROR(no_udev_error)])])
AC_ARG_WITH([system-bus-services-dir],
            [AS_HELP_STRING([--with-system-bus-services-dir],
                            [Path to the system bus services directory])],
            [system_bus_services_dir="$withval"],
            [PKG_CHECK_VAR([systembusservicesdir], [dbus-1],
                           [system_bus_services_dir], [],
                           [AC_MSG_ERROR(no_systembusservicesdir_error)])])
AC_ARG_WITH([modprobedir],
            [AS_HELP_STRING([--with-modprobedir],
                            [Path to the system modprobe.d directory])],
            [modprobedir="$withval"], [modprobedir="/lib/modprobe.d"])
AC_SUBST(modprobedir)
AC_ARG_WITH([dbussystemconfigdir],
            [AS_HELP_STRING([--with-dbussystemconfigdir],
                            [Path to the system dbus-1/system.d directory])],
            [dbussystemconfigdir="$withval"], [dbussystemconfigdir="/usr/share/dbus-1/system.d"])
AC_SUBST(dbussystemconfigdir)

FLATPAK_ARCH="x86_64"
case $target_cpu in
  arm*)
    FLATPAK_ARCH="arm"
  ;;
  aarch64*)
    FLATPAK_ARCH="aarch64"
  ;;
esac
AC_SUBST(FLATPAK_ARCH)

AC_CONFIG_FILES([
	Makefile
	dracut/Makefile
	dracut/image-boot/Makefile
	dracut/repartition/Makefile
	dracut/customization/Makefile
	factory-reset/Makefile
	fallback-fb-setup/Makefile
	flatpak-repos/Makefile
	nvidia/Makefile
	psi-monitor/Makefile
	record-boot-success/Makefile
	tests/Makefile
	tmpfiles.d/chromium-system-services.conf
])
AC_OUTPUT
