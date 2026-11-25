#!/usr/bin/python3
'''
Tests eos-live-storage-setup. Must be run as a user privileged enough to run
`losetup`. If run as an unprivileged user, all tests are skipped.
'''
from contextlib import contextmanager
import re
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
LINUX_TYPE = '0FC63DAF-8483-4772-8E79-3D69D8477DE4'
ESP_TYPE = 'C12A7328-F81F-11D2-BA4B-00A0C93EC93B'
STANDARD_PARTITION_TABLE = f'''
label: gpt
unit: sectors
label-id: 4BDEB166-7BE1-40D8-A73C-6555DB153BF5

start=        2048, size=     4251900, type={LINUX_TYPE}
start=     4255996, size=       28672, type={ESP_TYPE}
'''.strip().encode('ascii')  # noqa: E501


def _strip_uuids(table):
    '''Removes partition UUIDs, which are randomly generated for new
    partitions, from an sfdisk dump.'''
    return re.sub(r', uuid=[0-9A-Fa-f-]+', '', table)


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
label: gpt
label-id: 4BDEB166-7BE1-40D8-A73C-6555DB153BF5
device: {img_device}
unit: sectors
first-lba: 2048
last-lba: 8388574
sector-size: 512

{img_device}p1 : start=        2048, size=     4251900, type={linux}
{img_device}p2 : start=     4255996, size=       28672, type={esp}
{img_device}p3 : start=     4286464, size=     4100096, type={linux}
                    '''.strip().format(
                    img_device=img_device, linux=LINUX_TYPE, esp=ESP_TYPE)

                # Check that data partition was added as expected
                # Note that the values above also ensure that the data partition was
                # aligned to a 1mb boundary, leaving a few unused sectors after p2
                # and room for the secondary GPT header at the end of the disk.
                self.assertEqual(expected_table,
                                 _strip_uuids(new_table.strip()))

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
        table = f'''
start=        2048, size=     4251900, type={LINUX_TYPE}
start=     4255996, size=       28672, type={ESP_TYPE}
size=65536, type={LINUX_TYPE}
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
        table = f'''
start=        2048, size=     4251900, type={LINUX_TYPE}
start=     4255996, type={ESP_TYPE}
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
        table = f'''
start=        2048, size=     4251900, type={LINUX_TYPE}
start=     4255996, size=     4130000, type={ESP_TYPE}
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
