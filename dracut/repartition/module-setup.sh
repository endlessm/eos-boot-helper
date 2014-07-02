check() {
  return 0
}

depends() {
  echo fs-lib systemd
}

install() {
  dracut_install sfdisk
  dracut_install basename
  dracut_install readlink
  dracut_install mkswap
  inst_script "$moddir/endless-repartition.sh" /bin/endless-repartition
  inst_simple "$moddir/endless-repartition.service" \
	"$systemdsystemunitdir/endless-repartition.service"
  mkdir -p "${initdir}/$systemdsystemunitdir/initrd.target.wants"
  ln_r "$systemdsystemunitdir/endless-repartition.service" \
	"$systemdsystemunitdir/initrd.target.wants/endless-repartition.service"
}
