#!/bin/sh
# Copyright (C) 2014-2017 Endless Mobile, Inc.
# Licensed under the GPLv2
#
# The purpose of this script is to identify if we are running on target
# Endless hardware and if so, enlarges the root partition to use
# all available space.
#
# It is important to identify that this system is an Endless-flashed device
# that desires such treatment.

# For platforms using a GPT partition table, we do this by detecting that GPT
# flag #55 is set on the root partition, which is deliberately set in EOS
# images. If you need to avoid such repartitioning, just remove that flag
# before first boot.
#
# When dealing with a DOS partition table we do this by detecting that the type
# code for unused partition entry 4 has magic number 'dd', which is
# deliberately set in EOS images. If you need to avoid such repartitioning,
# just remove that 4th partition before first boot.
#
# The 55 flag (or the "dd" marker) is also removed after this script is run,
# providing a quick/cheap way of knowing that our work is done, avoiding going
# through all this logic on each boot.
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

if [ $# -ge 1 ]; then
  # For testing
  orig_root_part="$1"
else
  orig_root_part=$(systemctl show -p What sysroot.mount)
  orig_root_part=${orig_root_part#What=}
fi

if [ -z "${orig_root_part}" ]; then
  echo "repartition: couldn't identify root device"
  exit 0
fi

# Identify root partition device node and parent disk
root_part=$(readlink -f "${orig_root_part}")
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
# - SCSI/MMC/NVMe block devices with different naming conventions
# - A different partition numbering scheme as not all configurations have
#   a ESP and a BIOS boot partition.
# - Virtual block devices for OpenQA
partno=$(get_last_char ${root_part})
swap_partno=$((partno + 1))

case ${root_part} in
  /dev/[sv]d??)
    root_disk=${root_part%?}
    ;;
  /dev/*p[0-9])
    root_disk=${root_part%p?}
    ;;
esac

case ${orig_root_part} in
  /dev/mapper/endless-image?)
    root_disk=${orig_root_part%?}
    using_device_mapper=1
    ;;
  /dev/loop?p?)
    using_loop=1
    ;;
esac

if [ -z "${root_disk}" ]; then
  echo "repartition: no root disk found for $root_part"
  exit 0
fi

pt_label=$(blkid -o value -s PTTYPE $root_disk)
if [ -z "$pt_label" ]; then
  echo "repartition: blkid -o value -s PTTYPE '$root_disk' failed"
  exit 0
fi

# Check for our magic "this is Endless" marker
if [ "$pt_label" = "dos" ]; then
  marker=$(sfdisk --force --part-type $root_disk 4)
else
  marker=$(sfdisk --force --part-attrs $root_disk $partno)
fi

case "$marker" in
  *GUID:55* | dd)
    ;;
  *)
    echo "repartition: marker not found"
    exit 0
    ;;
esac

# udev might still be busy probing the disk, meaning that it will be in use.
udevadm settle

# take current partition table
parts=$(sfdisk -d $root_disk)

# if MBR avoid considering the magic marker partition (the last one)
if [ "$pt_label" = "dos" ]; then
  parts=$(echo "$parts" | sed -e '$d')
fi

# If we detect a recovery partition at the end of the disk, we'll be careful
# not to destroy it.
lastparttype=$(echo "$parts" | sed -n -e '$ s/.*type=\([A-F0-9-]\+\).*/\1/p')
if [ "$lastparttype" = "BFBFAFE7-A34F-448A-9A5B-6213EB736C22" \
    -o "$lastparttype" = "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7" ]; then
  # We'll use the free space up to where this partition starts
  preserve_start=$(echo "$parts" | sed -n -e '$ s/.*start=[ ]*\([^,]*\).*/\1/p')

  # Save the partition entry to be restored later, and delete it from the
  # list for now, to simplify the logic that follows.
  preserve_partition=$(echo "$parts" | sed -n -e '$ s/[^:]*:\(.*\)$/\1/p')
  parts=$(echo "$parts" | sed '$d')
fi

# check the last partition on the disk
lastpartno=$(echo "$parts" | sed -n -e '$ s/[^:]*\([0-9]\) :.*$/\1/p')

if [ $lastpartno -eq $swap_partno ]; then
  # We previously created an extra partition for swap.
  # Remove it, now that we are using zram instead of disk swap.
  # Keep in mind, though, that this code path currently only runs
  # if we had not yet completed the repartitioning, for example
  # in the rare case that we were halfway through creating a swap
  # partition on a previous version of the OS, but did not finish
  # before upgrading the OS.
  parts=$(echo "$parts" | sed '$d')
elif [ $lastpartno -gt $swap_partno ]; then
  echo "repartition: found $lastpartno partitions?"
  exit 0
fi

# calculate new partition sizes
disk_size=$(blockdev --getsz $root_disk)
part_size=$(blockdev --getsz $root_part)
part_start=$(echo "$parts" | sed -n -e '$ s/.*start=[ ]\+\([0-9]\+\).*$/\1/p')
part_end=$(( part_start + part_size ))
echo "Dsize $disk_size PreserveStart $preserve_start Psize $part_size Pstart $part_start Pend $part_end"

# Calculate the new root partition size, assuming that it will expand to fill
# all available space
if [ -n "$preserve_start" ]; then
  # Use free space up until the start of the preserve partition
  new_size=$(( preserve_start - part_start ))
else
  # Fill the remainder of the disk
  new_size=$(( disk_size - part_start ))

  # Subtract the size of the secondary GPT header at the end of the disk. We do
  # this also for MBR in case we want to convert MBR->GPT later
  new_size=$(( new_size - 33 ))
fi

# remove the last-lba line so that we fill the disk
# + Randomize PARTUUIDs
# + Randomize GPT disk UUID
parts=$(echo "$parts" | sed -e '/^last-lba:/d;s/ uuid=[a-fA-F0-9-]\{36\},\{0,1\}//;/^label-id:/d')

if [ $new_size -gt $part_size ]; then
  echo "Try to resize $root_part to fill $new_size sectors"
  parts=$(echo "$parts" | sed -e "$ s/size=[0-9\t ]*,/size=$new_size,/")
fi

# Readd the preserve partition that we excluded earlier
if [ -n "$preserve_partition" ]; then
  parts="$parts
$preserve_partition"
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

# Device-mapper needs an extra prod to update the block devices
if [ -n "$using_device_mapper" ]; then
  kpartx -u $root_disk
  udevadm settle
fi

# Loop devices need a different extra prod
if [ -n "$using_loop" ]; then
  partprobe $root_disk
  udevadm settle
fi

# Randomize root filesystem UUID
# uninit_bg functionality prevents us from doing this later when the
# filesystem is mounted.
tune2fs -U random $root_part
udevadm settle

# Now that we changed the UUID, the auto-generated units based on the
# kernel cmdline root= parameter are wrong. It's easy to override
# sysroot.mount here
mkdir -p /etc/systemd/system/sysroot.mount.d
cat <<EOF > /etc/systemd/system/sysroot.mount.d/50-newuuid.conf
[Mount]
What=$root_part
EOF

# systemd-fsck-root can't be fixed as above, because there's no way
# for a drop-in to fix the existing BindsTo= entry (a drop-in can only
# append another value). So we override the whole unit, using sed for the
# required manipulations.
# systemd-escape will escape "-" characters using backslashes, however
# sed ordinarily interprets backslashes as a syntax item. To avoid this,
# we must double up the backslashes first.
orig_root_part_escaped=$(systemd-escape -p $orig_root_part | sed -e 's:\\:\\\\:g')
root_part_escaped=$(systemd-escape -p $root_part | sed -e 's:\\:\\\\:g')
sed -e "s:$orig_root_part:$root_part:" \
  -e "s:$orig_root_part_escaped:$root_part_escaped:" \
  /run/systemd/generator/systemd-fsck-root.service \
  > /etc/systemd/system/systemd-fsck-root.service

# Make systemd aware of the unit file changes
/bin/systemctl daemon-reload

# Remove marker - must be done last, prevents this script from running again
# In the MBR case the marker partition is removed as part of sfdisk rewriting
# the partition table above
if [ "$pt_label" = "gpt" ]; then
  attrs=$(sfdisk --part-attrs $root_disk $partno)
  attrs=$(echo "$attrs" | sed -e 's/GUID:55//g')
  sfdisk --force --part-attrs $root_disk $partno "$attrs"
fi
udevadm settle

# Final update to SPL checksum
if [ -x /usr/sbin/amlogic-fix-spl-checksum ]; then
  /usr/sbin/amlogic-fix-spl-checksum $root_disk
  udevadm settle
fi

# During the above process, the rootfs block device momentarily goes away.
# This sometimes results in systemd cancelling various important parts
# of the bootup procedure. Retrigger here.
/bin/systemctl --no-block start initrd.target
