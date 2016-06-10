#!/bin/sh
# Copyright (C) 2016 Endless Mobile, Inc.
# Licensed under the GPLv2
#
# The purpose of this script is to make sure we boot a good rootfs.

bootloader_entries_dir="/sysroot/boot/loader/entries"
extensions_path="/sysroot/ostree/repo/extensions/eos"
uenv_path="/sysroot/boot/loader/uEnv.txt"
tmp_dir="${extensions_path}/tmp"

# read_cmdline_ostree reads the kernel command line and extracts the value of
# the "ostree" parameter.
#
# $1: kernel command line
# $2: the value of the "ostree" parameter (output variable)
read_cmdline_ostree () {
    local cmdline="${1}"
    local __output_var=${2}

    local link

    for p in ${cmdline}; do
        if [ "$(echo ${p} | cut -d= -f1)" = "ostree" ]; then
            link=$(echo ${p} | cut -d= -f2-)
            if [ -n ${link} ]; then
                eval $__output_var="'${link}'"
                return 0
            fi
        fi
    done

    return 1
}

# get_deployment_hash returns the kernel/initramfs hash of a deployment.
#
# $1: path of the deployment's root filesystem
# $2: the kernel/initramfs hash (output variable)
get_deployment_hash () {
    local rootfs=${1}
    local __output_var=${2}

    local deployment_hash

    for f in $(ls ${rootfs}/boot); do
        if [ $(echo ${f} | cut -d- -f1) = "vmlinuz" ]; then
            vmlinuz_hash=$(echo ${f} | rev | cut -d- -f1 | rev)
        elif [ $(echo ${f} | cut -d- -f1) = "initramfs" ]; then
            initramfs_hash=$(echo ${f} | rev | cut -d- -f1 | rev)
        fi
    done
    if [ -z ${vmlinuz_hash} -o -z ${initramfs_hash} -o ${vmlinuz_hash} != ${initramfs_hash} ]; then
        echo "robustness: missing or conflicting values for kernel and initramfs hashes"
        return 1
    fi

    deployment_hash=${vmlinuz_hash}

    eval $__output_var="'${deployment_hash}'"
    return 0
}

# get_bootloader_entry returns the path to the bootloader entry of the
# deployment that has a particular kernel/initramfs hash.
#
# $1: kernel/initramfs hash
# $2: the path to the bootloader entry containing the deployment (output variable)
get_bootloader_entry () {
    local deployment_hash=${1}
    local __output_var=${2}

    local bootloader_entry

    for f in "${bootloader_entries_dir}"/*; do
        if [ $(grep -c ${deployment_hash} ${f}) -gt 0 ]; then
            if [ -z ${bootloader_entry} ]; then
                bootloader_entry=${f}
            else
                echo "robustness: more than one bootloader entry with the same deployment hash"
                return 1
            fi
        fi
    done

    if [ -z ${bootloader_entry} ]; then
        echo "robustness: bootloader entry not found for hash ${deployment_hash}"
        return 1
    fi

    eval $__output_var=${bootloader_entry}
    return 0
}

# swap_files swaps two files on disk.
#
# $1: file 1
# $2: file 2
swap_files () {
    if [ ! -f ${1} ]; then
        echo "robustness: file ${1} doesn't exist"
        return 1
    fi
    if [ ! -f ${2} ]; then
        echo "robustness: file ${2} doesn't exist"
        return 1
    fi

    temp=$(mktemp -p $(dirname ${1}))
    mv ${1} ${temp} && \
        mv ${2} ${1} && \
        mv ${temp} ${2}
    if [ $? != 0 ]; then
        echo "robustness: error swapping files ${1} and ${2}"
        return 1
    fi

    return 0
}


read_cmdline_ostree "$(cat /proc/cmdline)" new_ostree_link
if [ $? != 0 ]; then
    echo "robustness: missing ostree parameter in kernel command line"
    exit 0
fi
new_deployment_link=/sysroot${new_ostree_link}

new_deployment_link_target=$(readlink ${new_deployment_link})
new_root=$(basename ${new_deployment_link_target})
new_root_path=$(readlink -f ${new_deployment_link})

deploys_directory=$(dirname ${new_root_path})

# check the bootloader entries to find the old root
for cfg_path in "${bootloader_entries_dir}"/*; do
    cfg=$(basename ${cfg_path})
    # check that the bootloader file starts with "ostree" and ends with ".conf"
    #   $ basename foo.conf .conf
    #   foo
    #   $ basename foo.confs .conf
    #   foo.confs
    if [ $(echo ${cfg} | cut -d- -f1) = "ostree" -a $(basename ${cfg} .conf) != ${cfg} ]; then
        read_cmdline_ostree "$(grep "ostree=" ${cfg_path})" ostree_link
        if [ $? != 0 ]; then
            echo "robustness: entry without ostree parameter in ${entries_dir}"
            exit 0
        fi
        if [ ${ostree_link} != ${new_ostree_link} ]; then
            old_deployment_link=/sysroot${ostree_link}
            old_deployment_link_target=$(readlink ${old_deployment_link})
            old_root=$(basename ${old_deployment_link_target})
            break
        fi
    fi
done

if [ -z ${old_root} ]; then
    echo "robustness: only one bootloader entry, booting it"
    exit 0
fi

old_root_hash=$(echo ${old_root} | cut -d "." -f 1)
new_root_hash=$(echo ${new_root} | cut -d "." -f 1)

old_root_path=${deploys_directory}/${old_root}

# check new root successful state
new_root_flags_path="${extensions_path}/boot-flags/${new_root_hash}"

if [ -f ${new_root_flags_path} ]; then
    # skip first line [boot-flags]
    for l in $(tail -n+2 ${new_root_flags_path}); do
        key="$(echo ${l} | cut -d= -f1)"
        value="$(echo ${l} | cut -d= -f2-)"
        case "${key}" in
            successful)
                successful="${value}"
                ;;
            tries_left)
                tries_left="${value}"
                ;;
            *)
                echo "robustness: malformed line in flags file: ${l}"
        esac
    done

    if [ -z ${successful} -o -z ${tries_left} ]; then
        echo "robustness: failed to parse flags file, booting the root specified in the kernel command line"
        exit 0
    fi

    echo successful=${successful}
    echo tries_left=${tries_left}

    if [ ${successful} = 1 ]; then
        # last boot successful, we can just boot
        # no need for the flags file anymore, we can delete it
        rm -f ${new_root_flags_path}
    elif [ ${tries_left} -gt 0 ]; then
        # first boot with an updated tree or last boot not successful but we
        # still have tries left, decrement tries_left and boot
        tries_left_updated=$((${tries_left} - 1))
        sed -i "s/tries_left=${tries_left}/tries_left=${tries_left_updated}/g" ${new_root_flags_path}
    else
        echo "Last boot unsuccessful and no more tries left, rolling back to previous version"
        get_deployment_hash ${new_root_path} new_deployment_hash
        if [ $? != 0 ]; then
            exit 0
        fi
        get_deployment_hash ${old_root_path} old_deployment_hash
        if [ $? != 0 ]; then
            exit 0
        fi
        get_bootloader_entry ${old_deployment_hash} old_bootloader_entry
        if [ $? != 0 ]; then
            exit 0
        fi
        get_bootloader_entry ${new_deployment_hash} new_bootloader_entry
        if [ $? != 0 ]; then
            exit 0
        fi

        mkdir -p ${tmp_dir}
        cat /proc/cmdline > ${tmp_dir}/cmdline
        sed -i "s/${new_deployment_hash}/${old_deployment_hash}/g" ${tmp_dir}/cmdline

        swap_files ${new_bootloader_entry} ${old_bootloader_entry}
        if [ $? != 0 ]; then
            exit 0
        fi

        if [ -f ${uenv_path} ]; then
            sed -i "s/${new_deployment_hash}/${old_deployment_hash}/g" ${uenv_path}
        fi

        # ostree uses "version" to decide whether to swap bootloader
        # configurations when doing a deploy, make sure the rolled-back
        # deployment has version 1. This allows deploying again the just
        # rolled-back deployment
        sed -i "s/^version [0-9]$/version 1/" ${old_bootloader_entry}
        sed -i "s/^version [0-9]$/version 2/" ${new_bootloader_entry}

        # signal userspace we rolled back so it can clean up and inform the
        # user
        echo ${new_root_hash} > ${extensions_path}/rolled-back

        # change /proc/cmdline so ostree reads the right value of "ostree=" on
        # this boot
        mount --bind ${tmp_dir}/cmdline /proc/cmdline
    fi
else
    echo "robustness: missing flags file, booting the root specified in the kernel command line"
fi
