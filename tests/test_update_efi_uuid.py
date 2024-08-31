# Copyright 2024 Endless OS Foundation LLC
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import shlex
import subprocess
import sys
from uuid import UUID

from .util import built_program, EFIVARFS_PATH

logger = logging.getLogger(__name__)

EFI_UPDATE_UUID = built_program('eos-update-efi-uuid')

ORIG_ESP_UUID = '9cf7d938-86c5-4f09-8401-fd0d6e4c646c'
NEW_ESP_UUID = '0de64583-f397-4783-a8f0-f101dd91def4'
OTHER_ESP_UUID = '5538ba7e-e641-4560-84c9-6194f68b8d32'
ENDLESS_LOAD_OPTION = 'Boot0003-8be4df61-93ca-11d2-aa0d-00e098032b8c'

# Offset info the EFI variable where the UUID is located. Note that this
# is dependent on the length of the title from EFI/endless/BOOTX64.CSV.
# This comes from the shim package and is currently "Endless OS".
UUID_OFFSET = 56


def run(cmd, check=True, log_level=logging.INFO, **kwargs):
    cmd_str = shlex.join(cmd)
    logger.log(log_level, f'Executing {cmd_str}')
    return subprocess.run(cmd, check=check, **kwargs)


def hexdump(path):
    proc = run(
        ['hexdump', '-C', str(path)],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
        log_level=logging.DEBUG,
    )
    return proc.stdout


def test_update(efivarfs):
    """Update with correct partition UUID"""
    run([EFI_UPDATE_UUID, '-v', ORIG_ESP_UUID, NEW_ESP_UUID])

    # Keep track of the hexdumps for a repeat.
    test_hexdumps = {}

    for test_path in efivarfs.iterdir():
        var = test_path.name
        test_hex = hexdump(test_path)
        test_hexdumps[str(test_path)] = test_hex
        src_path = EFIVARFS_PATH / var
        src_hex = hexdump(src_path)

        if test_path.name != ENDLESS_LOAD_OPTION:
            assert test_hex == src_hex, f'{var} has changed'
            continue

        assert test_hex != src_hex, f'{var} has not changed'
        with open(src_path, 'rb') as src, open(test_path, 'rb') as test:
            src_data = src.read()
            test_data = test.read()

            assert len(src_data) == len(test_data), f'{var} size has changed'

            # Up until the UUID offset should match.
            assert test_data[:UUID_OFFSET] == src_data[:UUID_OFFSET]

            # The next 16 bytes are the UUID.
            uuid_end = UUID_OFFSET + 16
            src_uuid = UUID(ORIG_ESP_UUID)
            test_uuid = UUID(NEW_ESP_UUID)
            if sys.byteorder == 'little':
                src_uuid_bytes = src_uuid.bytes_le
                test_uuid_bytes = test_uuid.bytes_le
            else:
                src_uuid_bytes = src_uuid.bytes
                test_uuid_bytes = test_uuid.bytes
            assert test_data[UUID_OFFSET:uuid_end] != src_data[UUID_OFFSET:uuid_end]
            assert src_data[UUID_OFFSET:uuid_end] == src_uuid_bytes
            assert test_data[UUID_OFFSET:uuid_end] == test_uuid_bytes

            # The rest should match.
            assert test_data[uuid_end:] == src_data[uuid_end:]

    # Running again should cause no changes since there aren't any load
    # options matching the original UUID.
    run([EFI_UPDATE_UUID, '-v', ORIG_ESP_UUID, NEW_ESP_UUID])
    for test_path in efivarfs.iterdir():
        test_hex = hexdump(test_path)
        prev_hex = test_hexdumps[str(test_path)]
        assert test_hex == prev_hex, f'{test_path.name} has changed'


def test_dry_run(efivarfs):
    """Dry run should produce no changes"""
    run([EFI_UPDATE_UUID, '-v', '--dry-run', ORIG_ESP_UUID, NEW_ESP_UUID])

    for test_path in efivarfs.iterdir():
        test_hex = hexdump(test_path)
        src_path = EFIVARFS_PATH / test_path.name
        src_hex = hexdump(src_path)

        assert test_hex == src_hex, f'{test_path.name} has changed'


def test_other(efivarfs):
    """Other partition UUID should produce no changes"""
    run([EFI_UPDATE_UUID, '-v', OTHER_ESP_UUID, NEW_ESP_UUID])

    for test_path in efivarfs.iterdir():
        test_hex = hexdump(test_path)
        src_path = EFIVARFS_PATH / test_path.name
        src_hex = hexdump(src_path)

        assert test_hex == src_hex, f'{test_path.name} has changed'
