# Copyright (C) 2016 Endless Mobile, Inc.
# Licensed under the GPLv2

check() {
  return 0
}

depends() {
  echo systemd
}

install() {
  dracut_install basename
  dracut_install cut
  dracut_install dirname
  dracut_install grep
  dracut_install mktemp
  dracut_install readlink
  dracut_install rev
  dracut_install sed
  dracut_install tail
  inst_script "$moddir/endless-robustness.sh" /bin/endless-robustness
  inst_simple "$moddir/endless-robustness.service" \
	"$systemdsystemunitdir/endless-robustness.service"
  mkdir -p "${initdir}/$systemdsystemunitdir/initrd.target.wants"
  ln_r "$systemdsystemunitdir/endless-robustness.service" \
	"$systemdsystemunitdir/initrd.target.wants/endless-robustness.service"
}
