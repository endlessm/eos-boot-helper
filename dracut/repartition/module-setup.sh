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
  inst_hook pre-mount 50 "$moddir/endless-repartition.sh"
}
