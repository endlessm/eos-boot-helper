#!/usr/bin/env python3
'''
Tests eos-repartition-mbr. Must be run as a user privileged enough to run
`losetup`. If run as an unprivileged user, all tests are skipped.
'''
from contextlib import contextmanager
import os
import re
from subprocess import check_call, check_output, CalledProcessError
import tempfile

from .util import (
    BaseTestCase,
    system_script,
    losetup,
    needs_root,
    sfdisk,
)


EOS_REPARTITION_MBR = system_script('eos-repartition-mbr')
SECTOR = 512
# Dummy bootloaders
MBR = b'x' * 440
BIOS_BOOT_OFFSET = 129024 * SECTOR
BIOS_BOOT = b'y' * (2014 * SECTOR)
DISK_SIZE_BYTES = 21 * (1024 ** 3)
STANDARD_PARTITION_TABLE = '''
label: gpt
unit: sectors

start=        2048, size=      126976, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B
start=      129024, size=        2048, type=21686148-6449-6E6F-744E-656564454649
start=      131072, size=    42762240, type=4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709, attrs=GUID:55
'''.strip().encode('ascii')  # noqa: E501


def check_bootloader(img):
    img.seek(0)
    assert img.read(len(MBR)) == MBR

    img.seek(BIOS_BOOT_OFFSET)
    assert img.read(len(BIOS_BOOT)) == BIOS_BOOT


def check_gpts(img, expected):
    n = len(expected)

    img.seek(SECTOR)
    assert img.read(n) == expected

    img.seek(-SECTOR, os.SEEK_END)
    assert img.read(n) == expected


@contextmanager
def _prepare(initial_table):
    with tempfile.NamedTemporaryFile(buffering=0) as img:
        img.write(MBR)

        img.seek(BIOS_BOOT_OFFSET)
        img.write(BIOS_BOOT)

        img.truncate(DISK_SIZE_BYTES)

        sfdisk(img.name, initial_table)

        # Double-check that the image looks right before we start
        check_bootloader(img)
        check_gpts(img, b'EFI PART')

        with losetup(img.name) as img_device:
            yield img, img_device


class TestRepartitionMbr(BaseTestCase):
    @needs_root
    def test_repartition_mbr(self):
        with _prepare(STANDARD_PARTITION_TABLE) as (img, img_device):
            try:
                check_call([EOS_REPARTITION_MBR, img_device])

                new_table = check_output(["sfdisk", "--dump", img_device],
                                         universal_newlines=True)
                # Normalize the one bit that varies
                new_table = re.sub(r'^label-id: 0x[0-9a-f]{8}$',
                                   '''label-id: 0xdeadbeef''',
                                   new_table,
                                   flags=re.MULTILINE)

                expected_table = '''
label: dos
label-id: 0xdeadbeef
device: {img_device}
unit: sectors

{img_device}p1 : start=        2048, size=      126976, type=ef
{img_device}p2 : start=      131072, size=    42762240, type=83, bootable
{img_device}p4 : start=           0, size=           0, type=dd
                    '''.strip().format(img_device=img_device).split('\n')

                assert expected_table == new_table.strip().split('\n')

                # BIOS bootloaders should be intact
                check_bootloader(img)

                # GPTs should be erased
                check_gpts(img, b'\0' * SECTOR)
            except:
                # Log the current state to aid debugging
                check_call(["sfdisk", "--dump", img_device])
                raise

    @needs_root
    def test_fails_if_esp_missing(self):
        self._test_missing(0)

    @needs_root
    def test_fails_if_bios_boot_missing(self):
        self._test_missing(1)

    @needs_root
    def test_fails_if_root_missing(self):
        self._test_missing(2)

    def _test_missing(self, index):
        lines = STANDARD_PARTITION_TABLE.split(b'\n')
        i = index + 3
        initial_table = b'\n'.join(lines[:i] + lines[i+1:])

        self._test_fails(initial_table)

    @needs_root
    def test_fails_with_swap_partition(self):
        initial_table = STANDARD_PARTITION_TABLE + b'''
start=    42893312, size=     1024000, type=0657FD6D-A4AB-43C4-84E5-0933C84B4F4F'''  # noqa: E501

        self._test_fails(initial_table)

    @needs_root
    def test_fails_with_unknown_partition(self):
        # type= is a fresh UUID generated for this test
        initial_table = STANDARD_PARTITION_TABLE + b'''
start=    42893312, size=     1024000, type=18B660C0-CAB5-4990-8898-07169F986163'''  # noqa: E501

        self._test_fails(initial_table)

    def _test_fails(self, initial_table):
        with _prepare(initial_table) as (img, img_device):
            # Read back the partition table. This includes extra fields like
            # 'label-id' and the device path, both of which vary between runs.
            # It's easier to do this than to try to post-process new_table to
            # make it match initial_table.
            written_table = check_output(["sfdisk", "--dump", img_device],
                                         universal_newlines=True)

            with self.assertRaises(CalledProcessError):
                check_call([EOS_REPARTITION_MBR, img_device])

            # Check nothing was modified
            new_table = check_output(["sfdisk", "--dump", img_device],
                                     universal_newlines=True)
            assert written_table.split('\n') == new_table.split('\n')
            check_bootloader(img)
            check_gpts(img, b'EFI PART')
