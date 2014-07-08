#!/bin/sh
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

exec > /dev/kmsg
exec 2>&1

# Identify root partition device node and parent disk
root_part=$(readlink -f /dev/disk/by-label/ostree)
if [ -z ${root_part} ]; then
  echo "repartition: no root found"
  exit 0
fi

case ${root_part} in
  /dev/mmcblk?p2)
    root_disk=${root_part%p2}
    swap_part=${root_part%?}3
    ;;
  /dev/sd?2)
    root_disk=${root_part%2}
    swap_part=${root_part%?}3
    ;;
esac

if [ -z "${root_disk}" ]; then
  echo "repartition: no root disk found for $root_part"
  exit 0
fi

# We should also check that we are working with a MBR partition table, to
# avoid destroying any non-Endless GPT setup.
# This is implicit below: a GPT setup will have a protective MBR with a single
# partition entry, it will not have the marker partition.
# There is still a chance that a secondary GPT header can be found on the last
# sector of the disk, so we must also use "--force" so that sfdisk doesn't
# bail out in such situations.

# Check for our magic "this is Endless" marker
marker=$(sfdisk --force --print-id $root_disk 4)
if [ "$marker" != "dd" ]; then
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

# If we find ourselves with >100GB free space, we'll use the final 4GB as
# a swap partition
new_size=$(( disk_size - part_start ))
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

if [ $new_size -gt $part_size ]; then
  # udev might still be busy probing the disk, meaning that it will be in use.
  udevadm settle

  echo "Try to resize $root_part to fill $new_size sectors"
  echo ",$new_size,," | sfdisk --force --no-reread -N2 -uS -S 32 -H 32 $root_disk
  echo "sfdisk returned $?"
  udevadm settle
fi

if [ -n "$swap_start" ]; then
  # Create swap partition
  echo "Create swap partition at $swap_start"
  echo "$swap_start,+,S," | sfdisk --force --no-reread -N3 -uS -S 32 -H 32 $root_disk
  echo "sfdisk returned $?"
  udevadm settle
fi

[ -e "$swap_part" ] && mkswap -L eos-swap $swap_part

# Remove marker - must be done last, prevents this script from running again
sfdisk --force --change-id $root_disk 4 0
udevadm settle
