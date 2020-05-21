# Copyright (C) 2016-2017 Endless Mobile, Inc.
# Licensed under the GPLv2

check() {
  return 0
}

depends() {
  echo systemd dm
}

install() {
  dracut_install blockdev kpartx dmsetup dumpexfat ntfsextents lsblk losetup
  instmods overlay
  inst_rules 60-cdrom_id.rules
  inst_script "$moddir"/eos-image-boot-setup /bin/eos-image-boot-setup
  inst_script "$moddir"/eos-live-storage-setup /bin/eos-live-storage-setup
  inst_script "$moddir"/eos-map-image-file /bin/eos-map-image-file
  inst_simple "$moddir"/eos-image-boot-setup.service \
	"$systemdsystemunitdir"/eos-image-boot-setup.service
  mkdir -p "${initdir}${systemdsystemconfdir}/initrd-switch-root.target.wants"
  inst_script "$moddir/eos-image-boot-generator" $systemdutildir/system-generators/eos-image-boot-generator
}
