#!/bin/sh
# The purpose of this script is to identify if we are running on target
# Endless hardware and if so, modify the partition table so that the root
# partition fills the disk.
#
# It is important to identify an Endless device in a quick/cheap way.
# We have such a mechanism in place just in case we might want to install
# Endless on another setup at some point (e.g. for demo purposes).
# To identify this, we check that the data partition is at partition 2,
# there are no further partitions on the disk, and the type code for unused
# partition entry 4 has magic number 'dd'.
#
# Based on code from dracut-modules-olpc.

exec > /dev/kmsg
exec 2>&1

if [ -f /dracut-state.sh ]; then
    . /dracut-state.sh 2>/dev/null
fi

# Identify root partition device node and parent disk
root_part=$(readlink -f ${root#block:})
if [ -z ${root_part} ]; then
  echo "resize: no root found"
  exit 0
fi

case ${root_part} in
  /dev/mmcblk?p2) root_disk=${root_part%p2} ;;
  /dev/sd?2) root_disk=${root_part%2} ;;
esac

if [ -z "${root_disk}" ]; then
  echo "resize: no root disk found for $root_part"
  exit 0
fi

# Check that our partition is the final partition
if [ -e "${root_disk}3" -o -e "${root_disk}4" -o -e "${root_disk}p3" -o -e "${root_disk}p4" ]; then
  echo "resize: extra partitions found, not resizing"
  exit 0
fi

# Check that our partition doesn't already fill the disk
root_disk_name=${root_disk#/dev/}
root_part_name=${root_part#/dev/}
disk_size=$(cat /sys/class/block/$root_disk_name/size)
part_size=$(cat /sys/class/block/$root_part_name/size)
part_start=$(cat /sys/class/block/$root_part_name/start)
part_end=$(( part_start + part_size ))
echo "Dsize $disk_size Psize $part_size Pstart $part_start Pend $part_end"
[ "$part_end" = "$disk_size" ] && exit 0

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
  echo "resize: marker not found"
  exit 0
fi

# udev might still be busy probing the disk, meaning that it will be in
# use. Give it a chance to finish first.
udevadm settle

echo "Try to resize $root_disk"
echo ",+,," | sfdisk --force --no-reread -N2 -uS -S 32 -H 32 $root_disk
echo "sfdisk returned $?"

# Remove marker
sfdisk --force --change-id $root_disk 4 0

# Partition nodes are removed and recreated now - wait for udev to finish
# recreating them before trying to mount the disk.
udevadm settle
