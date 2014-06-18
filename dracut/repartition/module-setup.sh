# Copyright (C) 2014 Endless Mobile, Inc.
# Licensed under the GPLv2

check() {
  return 0
}

depends() {
  echo fs-lib
}

install() {
  dracut_install sfdisk
  dracut_install basename
  dracut_install readlink
  dracut_install mkswap
  inst_hook pre-mount 50 "$moddir/endless-repartition.sh"
}
