#!/bin/bash

# Copyright 2023 Endless OS Foundation, LLC
# SPDX-License-Identifier: GPL-2.0-or-later

# Gather test data in the format eos-esp-generator uses. Install this in
# /etc/systemd/system-generators/ to gather data during boot and
# systemctl daemon-reload. Test data will be written to
# /run/espgen-data-*.tar.gz. Keep the command options below in sync with
# it.

set -e
shopt -s nullglob

usage() {
    cat <<EOF
Usage: $0 [OPTION]...

  -p, --print	print the data instead of saving it
  -h, --help	display this help and exit
EOF
}

ARGS=$(getopt -n "$0" -o ph -l print,help -- "$@")
eval set -- "$ARGS"

PRINT=false
while true; do
    case "$1" in
        -p|--print)
            PRINT=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "error: Unrecognized argument \"$1\"" >&2
            exit 1
            ;;
    esac
done

if [ -n "$SYSTEMD_SCOPE" ]; then
    export TMPDIR=/run
    exec >/dev/kmsg
fi

[ "$UID" -eq 0 ] && SUDO= || SUDO=sudo

datatmpdir=$(mktemp -d --tmpdir espgen-data-XXXXXXXX)
trap 'rm -rf "$datatmpdir"' EXIT
datadir_name=espgen-data
datadir="$datatmpdir/$datadir_name"
mkdir "$datadir"

# Make sure if /boot or /efi are automounts, the real mounts are
# triggered.
test -e /boot || :
test -e /efi || :

findmnt \
    --json \
    --list \
    --canonicalize \
    --evaluate \
    --nofsroot \
    --output \
    'TARGET,SOURCE,MAJ:MIN,FSTYPE,FSROOT,OPTIONS' \
    --real \
    > "$datadir/mounts.json"
if "$PRINT"; then
    echo "mounts.json:"
    cat "$datadir/mounts.json"
fi

findmnt \
    --json \
    --list \
    --canonicalize \
    --evaluate \
    --nofsroot \
    --output \
    'TARGET,SOURCE,FSTYPE,OPTIONS' \
    --fstab \
    > "$datadir/fstab.json"
if "$PRINT"; then
    echo "fstab.json:"
    cat "$datadir/fstab.json"
fi

for sys_block in /sys/block/*; do
    partitions=("$sys_block"/*/partition)
    [ ${#partitions[@]} -eq 0 ] && continue
    name=${sys_block##*/}
    $SUDO sfdisk --json "/dev/$name" > "$datadir/disk-${name}.json"
    if "$PRINT"; then
        echo "disk-${name}.json:"
        cat "$datadir/disk-${name}.json"
    fi
done

if ! "$PRINT"; then
    datafile=$(mktemp --tmpdir "${datadir_name}-XXXXXXXX.tar.gz")
    chmod 644 "$datafile"
    echo "Storing espgen test data in $datafile"
    tar -C "$datatmpdir" -czf "$datafile" "$datadir_name"
fi
