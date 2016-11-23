#!/bin/sh
# Copyright (C) 2014-2016 Endless Mobile, Inc.
# Licensed under the GPLv2
#
# The purpose of this script is to identify if we are running on target
# Endless hardware and if so, enlarges the root partition to use
# all available space.
# When disk space is plentiful, we also carve out some space at the end of
# the disk, and use it to create a swap partition.
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

orig_root_part=$(systemctl show -p What sysroot.mount)
orig_root_part=${orig_root_part#What=}
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

case ${orig_root_part} in
  /dev/mapper/endless-image?)
    root_disk=${orig_root_part%?}
    swap_part=${root_disk}${swap_partno}
    using_device_mapper=1
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
if [ "$pt_label" == "dos" ]; then
  marker=$(sfdisk --force --part-type $root_disk 4)
  swap_type="82"
else
  marker=$(sfdisk --force --part-attrs $root_disk $partno)
  swap_type="0657FD6D-A4AB-43C4-84E5-0933C84B4F4F"
fi

if [ "$marker" != "dd" ] && [ "$marker" != "GUID:55" ]; then
  echo "repartition: marker not found"
  exit 0
fi

# udev might still be busy probing the disk, meaning that it will be in use.
udevadm settle

# take current partition table
parts=$(sfdisk -d $root_disk)

# if MBR avoid considering the magic marker partition (the last one)
if [ "$pt_label" = "dos" ]; then
  parts=$(echo "$parts" | sed -e '$d')
fi

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

# calculate new partition sizes
disk_size=$(blockdev --getsz $root_disk)
part_size=$(blockdev --getsz $root_part)
part_start=$(echo "$parts" | sed -n -e '$ s/.*start=[ ]\+\([0-9]\+\).*$/\1/p')
part_end=$(( part_start + part_size ))
echo "Dsize $disk_size Psize $part_size Pstart $part_start Pend $part_end"

# Calculate the new root partition size, assuming that it will expand to fill
# the remainder of the disk
new_size=$(( disk_size - part_start ))

# Subtract the size of the secondary GPT header at the end of the disk. We do
# this also for MBR in case we want to convert MBR->GPT later
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

# remove the last-lba line so that we fill the disk
# + Randomize PARTUUIDs
# + Randomize GPT disk UUID
parts=$(echo "$parts" | sed -e '/^last-lba:/d;s/ uuid=.*//;/^label-id:/d')

if [ $new_size -gt $part_size ]; then
  echo "Try to resize $root_part to fill $new_size sectors"
  parts=$(echo "$parts" | sed -e "$ s/size=[0-9\t ]*,/size=$new_size,/")
fi

if [ -n "$swap_start" ]; then
  # Create swap partition
  echo "Create swap partition at $swap_start"
  parts="$parts
start=$swap_start, type=$swap_type"
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

[ -e "$swap_part" ] && mkswap -L eos-swap $swap_part

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
# append another value). So we override the whole unit.
sed -e "s:$orig_root_part:$root_part:" \
  -e "s:$(systemd-escape $orig_root_part):$(systemd-escape $root_part):" \
  /run/systemd/generator/systemd-fsck-root.service \
  > /etc/systemd/system/systemd-fsck-root.service

# Make systemd aware of the unit file changes
/bin/systemctl daemon-reload

# Remove marker - must be done last, prevents this script from running again
# In the MBR case the marker partition is removed as part of sfdisk rewriting
# the partition table above
if [ "$pt_label" = "gpt" ]; then
  sfdisk --force --part-attrs $root_disk $partno ''
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
