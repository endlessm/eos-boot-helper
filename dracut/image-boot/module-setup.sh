# Copyright (C) 2016 Endless Mobile, Inc.
# Licensed under the GPLv2

check() {
  return 0
}

depends() {
  echo systemd
}

install() {
  dracut_install blockdev kpartx dmsetup dumpexfat ntfsextents lsblk losetup
  instmods overlay
  inst_rules 55-dm.rules 60-cdrom_id.rules
  inst_script "$moddir"/eos-image-boot-setup /bin/eos-image-boot-setup
  inst_simple "$moddir"/eos-image-boot-setup.service \
	"$systemdsystemunitdir"/eos-image-boot-setup.service
  inst_simple "$moddir"/eos-live-etc-setup.service \
	"$systemdsystemunitdir"/eos-live-etc-setup.service
  mkdir -p "${initdir}${systemdsystemconfdir}/initrd-switch-root.target.wants"
  ln_r "${systemdsystemunitdir}/eos-live-etc-setup.service" \
        "${systemdsystemconfdir}/initrd-switch-root.target.wants/eos-live-etc-setup.service"
  inst_script "$moddir/eos-image-boot-generator" $systemdutildir/system-generators/eos-image-boot-generator
}
