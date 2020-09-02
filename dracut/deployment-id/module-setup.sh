# Copyright (C) 2020 Endless OS Foundation LLC
# Licensed under the GPLv2

check() {
  return 0
}

depends() {
  echo systemd
}

install() {
  dracut_install attr
  inst_script "$moddir/eos-metrics-deployment-id-setup" \
    /bin/eos-metrics-deployment-id-setup
  inst_simple "$moddir/eos-metrics-deployment-id-setup.service" \
    "$systemdsystemunitdir/eos-metrics-deployment-id-setup.service"
  mkdir -p "${initdir}/$systemdsystemunitdir/initrd.target.wants"
  ln_r "$systemdsystemunitdir/eos-metrics-deployment-id-setup.service" \
    "$systemdsystemunitdir/initrd.target.wants/eos-metrics-deployment-id-setup.service"
}
