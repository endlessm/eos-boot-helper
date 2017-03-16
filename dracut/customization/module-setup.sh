# Copyright (C) 2017 Endless Mobile, Inc.
# Licensed under the GPLv2

check() {
  return 0
}

depends() {
  echo systemd
}

install() {
  dracut_install sed
  inst_script "$moddir/eos-install-custom-boot-splash" \
    /bin/eos-install-custom-boot-splash
  inst_simple "$moddir/eos-install-custom-boot-splash.service" \
    "$systemdsystemunitdir/eos-install-custom-boot-splash.service"
  mkdir -p "${initdir}/$systemdsystemunitdir/plymouth-start.service.wants"
  ln_r "$systemdsystemunitdir/eos-install-custom-boot-splash.service" \
    "$systemdsystemunitdir/plymouth-start.service.wants/eos-install-custom-boot-splash.service"
}
