# Copyright (C) 2016-2017 Endless Mobile, Inc.
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
  inst_rules 55-dm.rules 60-cdrom_id.rules 95-dm-notify.rules
  inst_script "$moddir"/eos-image-boot-setup /bin/eos-image-boot-setup
  inst_script "$moddir"/eos-live-early-overlayfs-setup /bin/eos-live-early-overlayfs-setup
  inst_script "$moddir"/eos-map-image-file /bin/eos-map-image-file
  inst_simple "$moddir"/eos-image-boot-setup.service \
	"$systemdsystemunitdir"/eos-image-boot-setup.service
  inst_simple "$moddir"/eos-live-early-overlayfs-setup.service \
	"$systemdsystemunitdir"/eos-live-early-overlayfs-setup.service
  mkdir -p "${initdir}${systemdsystemconfdir}/initrd-switch-root.target.wants"
  ln_r "${systemdsystemunitdir}/eos-live-early-overlayfs-setup.service" \
        "${systemdsystemconfdir}/initrd-switch-root.target.wants/eos-live-early-overlayfs-setup.service"
  inst_script "$moddir/eos-image-boot-generator" $systemdutildir/system-generators/eos-image-boot-generator
}
