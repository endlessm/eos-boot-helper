#!/bin/sh
# Copyright (C) 2014 Endless Mobile, Inc.
# Licensed under the GPLv2
#
# The purpose of this script is to identify if we are running on target
# Endless hardware and if so, enlarges partition 2 (data partition) to use
# all available space.
# When disk space is plentiful, we also carve out some space at the end of
# the disk, and use it to create a swap partition (partition 3).
#
# It is important to identify that this system is an Endless-flashed device
# that desires such treatment. We do this by detecting that the type code for
# unused partition entry 4 has magic number 'dd', which is deliberately set in
# EOS images. If you need to avoid such repartitioning, just remove that 4th
# partition before first boot.
#
# The dd "marker" is also removed after this script is run, providing a
# quick/cheap way of knowing that our work is done, avoiding going through
# all this logic on each boot.
#
# This script is written carefully so that it can be interrupted after each
# operation, on next boot it should effectively continue where it left off.
#
# Special attention is given to the fact that modifying the partition table
# causes the kernel to re-read the partition table, which causes udev to
# quickly remove and recreate device nodes for affected disks. We call
# "udevadm settle" after each partition table change to make sure that udev
# has caught up with these events.
#
# Based on code from dracut-modules-olpc.

# Use dracut-lib.sh for root= /proc/cmdline parsing
. /lib/dracut-lib.sh

# Identify root partition device node and parent disk
root_arg=$(getarg root=)
case "$root_arg" in
  UUID=*)
    root_part="/dev/disk/by-uuid/${root_arg#UUID=}"
    ;;
  LABEL=*)
    root_part="/dev/disk/by-label/${root_arg#LABEL=}"
    ;;
  /dev/*)
    root_part="$root_arg"
    ;;
  *)
    echo "repartition: unrecognized root argument $root_arg"
    exit 0
    ;;
esac
root_part=$(readlink -f "$root_part")
if [ -z ${root_part} ]; then
  echo "repartition: no root found"
  exit 0
fi

get_last_char() {
	ret=$1
	while [ "${#ret}" != "1" ]; do
		ret=${ret#?}
	done
	echo $ret
}

# We have to work with a variety of setups here:
# - Either SCSI or MMC block devices with different naming conventions
# - A different partition numbering scheme as not all configurations have
#   a ESP and a BIOS boot partition.
partno=$(get_last_char ${root_part})
swap_partno=$((partno + 1))
case ${root_part} in
  /dev/mmcblk?p?)
    root_disk=${root_part%p?}
    swap_part=${root_disk}p${swap_partno}
    ;;
  /dev/sd??)
    root_disk=${root_part%?}
    swap_part=${root_disk}${swap_partno}
    ;;
esac

if [ -z "${root_disk}" ]; then
  echo "repartition: no root disk found for $root_part"
  exit 0
fi

# Check for our magic "this is Endless" marker
marker=$(sfdisk --force --part-attrs $root_disk $partno)
if [ "$marker" != "GUID:55" ]; then
  echo "repartition: marker not found"
  exit 0
fi

root_disk_name=${root_disk#/dev/}
root_part_name=${root_part#/dev/}
disk_size=$(cat /sys/class/block/$root_disk_name/size)
part_size=$(cat /sys/class/block/$root_part_name/size)
part_start=$(cat /sys/class/block/$root_part_name/start)
part_end=$(( part_start + part_size ))
echo "Dsize $disk_size Psize $part_size Pstart $part_start Pend $part_end"

# Calculate the new root partition size, assuming that it will expand to fill
# the remainder of the disk
new_size=$(( disk_size - part_start ))

# Subtract the size of the secondary GPT header at the end of the disk
new_size=$(( new_size - 33 ))

# If we find ourselves with >100GB free space, we'll use the final 4GB as
# a swap partition
added_space=$(( new_size - part_size ))
if [ $added_space -gt 209715200 ]; then
  new_size=$(( new_size - 8388608 ))
  swap_start=$(( part_start + new_size ))

  # Align swap partition start to 1MB boundary
  residue=$(( swap_start % 2048 ))
  if [ $residue -gt 0 ]; then
    swap_start=$(( swap_start + 2048 - residue ))
    # might as well bump up root partition size too, instead of leaving a gap
    new_size=$(( new_size + 2048 - residue ))
  fi
fi

# udev might still be busy probing the disk, meaning that it will be in use.
udevadm settle

# take current partition table
parts=$(sfdisk -d $root_disk)

# check the last partition on the disk
lastpart=$(echo "$parts" | sed -n -e '$ s/[^:]*\([0-9]\) :.*$/\1/p')

if [ $lastpart -eq $swap_partno ]; then
  # already have an extra partition, perhaps we were halfway through creating
  # a swap partition but didn't finish. Remove it to try again below.
  parts=$(echo "$parts" | sed '$d')
elif [ $lastpart -gt $swap_partno ]; then
  echo "repartition: found $lastpart partitions?"
  exit 0
fi

# remove the last-lba line so that we fill the disk
parts=$(echo "$parts" | sed -e '/^last-lba:/d')

if [ $new_size -gt $part_size ]; then
  echo "Try to resize $root_part to fill $new_size sectors"
  parts=$(echo "$parts" | sed -e "$ s/size=[0-9\t ]*,/size=$new_size,/")
fi

if [ -n "$swap_start" ]; then
  # Create swap partition
  echo "Create swap partition at $swap_start"
  parts="$parts
start=$swap_start, type=0657FD6D-A4AB-43C4-84E5-0933C84B4F4F"
fi

echo "$parts"
echo "$parts" | sfdisk --force --no-reread $root_disk
ret=$?
echo "sfdisk returned $ret"
udevadm settle

# Update SPL checksum right away, minimizing the time during which it is
# invalid
if [ -x /usr/sbin/amlogic-fix-spl-checksum ]; then
  /usr/sbin/amlogic-fix-spl-checksum $root_disk
  udevadm settle
fi

[ "$ret" != "0" ] && exit 0

[ -e "$swap_part" ] && mkswap -L eos-swap $swap_part

# Remove marker - must be done last, prevents this script from running again
sfdisk --force --part-attrs $root_disk $partno ''
udevadm settle

# Final update to SPL checksum
if [ -x /usr/sbin/amlogic-fix-spl-checksum ]; then
  /usr/sbin/amlogic-fix-spl-checksum $root_disk
  udevadm settle
fi
