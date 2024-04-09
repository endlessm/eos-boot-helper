#!/usr/bin/python3
'''
Tests eos-live-storage-setup. Must be run as a user privileged enough to run
`losetup`. If run as an unprivileged user, all tests are skipped.
'''
from contextlib import contextmanager
from subprocess import check_call, check_output
import tempfile

from .util import (
    BaseTestCase,
    dracut_script,
    losetup,
    needs_root,
    sfdisk,
)


EOS_LIVE_STORAGE_SETUP = dracut_script('image-boot', 'eos-live-storage-setup')
DISK_SIZE_BYTES = 4 * (1024 ** 3)
STANDARD_PARTITION_TABLE = '''
label: dos
unit: sectors
label-id: 0xdeadbeef

start=        2048, size=     4251900, type=0, bootable
start=     4255996, size=       28672, type=ef
'''.strip().encode('ascii')  # noqa: E501


@contextmanager
def _prepare(initial_table):
    with tempfile.NamedTemporaryFile(buffering=0) as img:
        img.truncate(DISK_SIZE_BYTES)
        sfdisk(img.name, initial_table)

        with losetup(img.name) as img_device:
            yield img, img_device


class TestLiveStorage(BaseTestCase):
    @needs_root
    def test_data_partition_added(self):
        with _prepare(STANDARD_PARTITION_TABLE) as (img, img_device):
            try:
                check_call([EOS_LIVE_STORAGE_SETUP, img_device + "p1"])

                new_table = check_output(["sfdisk", "--dump", img_device],
                                         universal_newlines=True)
                expected_table = '''
label: dos
label-id: 0xdeadbeef
device: {img_device}
unit: sectors
sector-size: 512

{img_device}p1 : start=        2048, size=     4251900, type=0, bootable
{img_device}p2 : start=     4255996, size=       28672, type=ef
{img_device}p3 : start=     4286464, size=     4102144, type=83
                    '''.strip().format(img_device=img_device)

                # Check that data partition was added as expected
                # Note that the values above also ensure that the data partition was
                # aligned to a 1mb boundary, leaving a few unused sectors after p2.
                self.assertEqual(expected_table, new_table.strip())

                # Check that the marker was written
                with open(img_device + "p3", "r") as fd:
                    self.assertEqual(fd.read(27),
                                     "endless_live_storage_marker")
            except Exception:
                # Log the current state to aid debugging
                check_call(["sfdisk", "--dump", img_device])
                raise

    # Test that no action is taken if we already have 3 partitions
    @needs_root
    def test_already_have_data_partition(self):
        table = '''
start=        2048, size=     4251900, type=0, bootable
start=     4255996, size=       28672, type=ef
size=65536, type=83
'''.strip().encode('ascii')  # noqa: E501
        with _prepare(table) as (img, img_device):
            try:
                orig_table = check_output(["sfdisk", "--dump", img_device],
                                          universal_newlines=True)

                check_call([EOS_LIVE_STORAGE_SETUP, img_device + "p1"])

                new_table = check_output(["sfdisk", "--dump", img_device],
                                         universal_newlines=True)
                self.assertEqual(orig_table, new_table)
            except Exception:
                # Log the current state to aid debugging
                check_call(["sfdisk", "--dump", img_device])
                raise

    # Test that no action is taken if the disk was already completely full
    @needs_root
    def test_no_space_available(self):
        table = '''
start=        2048, size=     4251900, type=0, bootable
start=     4255996, type=ef
'''.strip().encode('ascii')  # noqa: E501
        with _prepare(table) as (img, img_device):
            try:
                orig_table = check_output(["sfdisk", "--dump", img_device],
                                          universal_newlines=True)

                check_call([EOS_LIVE_STORAGE_SETUP, img_device + "p1"])

                new_table = check_output(["sfdisk", "--dump", img_device],
                                         universal_newlines=True)
                self.assertEqual(orig_table, new_table)
            except Exception:
                # Log the current state to aid debugging
                check_call(["sfdisk", "--dump", img_device])
                raise

    # Test that no action is taken if the disk doesn't have much space left
    @needs_root
    def test_not_much_space_available(self):
        table = '''
start=        2048, size=     4251900, type=0, bootable
start=     4255996, size=     4130000, type=ef
'''.strip().encode('ascii')  # noqa: E501
        with _prepare(table) as (img, img_device):
            try:
                orig_table = check_output(["sfdisk", "--dump", img_device],
                                          universal_newlines=True)

                check_call([EOS_LIVE_STORAGE_SETUP, img_device + "p1"])

                new_table = check_output(["sfdisk", "--dump", img_device],
                                         universal_newlines=True)
                self.assertEqual(orig_table, new_table)
            except Exception:
                # Log the current state to aid debugging
                check_call(["sfdisk", "--dump", img_device])
                raise
