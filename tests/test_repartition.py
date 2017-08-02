#!/usr/bin/env python3
'''
Tests endless-repartition.sh. Must be run as a user privileged enough to run
`losetup`. If run as an unprivileged user, all tests are skipped.
'''
from subprocess import check_call
import tempfile

from .util import (
    BaseTestCase,
    dracut_script,
    losetup,
    needs_root,
    partprobe,
    sfdisk,
    udevadm_settle,
)


ENDLESS_REPARTITION_SH = dracut_script('repartition', 'endless-repartition.sh')


class TestRepartition(BaseTestCase):
    @needs_root
    def test_creates_swap(self):
        '''
        This disk is big, so we should create a swap partition at the end.
        '''

        disk_size_bytes = 256071351296
        partition_table = '''
label: gpt
unit: sectors

start=        2048, size=      126976, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B
start=      129024, size=        2048, type=21686148-6449-6E6F-744E-656564454649
start=      131072, size=       20.4G, type=4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709, attrs=GUID:55
        '''.strip().encode('utf-8')  # noqa: E501

        self._go(disk_size_bytes, partition_table, swap='p4')

    @needs_root
    def test_preserves_basic_data_no_swap(self):
        '''
        This disk is too small to create a swap partition, but it does have a
        trailing NTFS partition. It should be preserved, and not formatted as
        swap.
        '''

        disk_size_bytes = 128035675648
        partition_table = '''
label: gpt
unit: sectors

start=        2048, size=      126976, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B
start=      129024, size=        2048, type=21686148-6449-6E6F-744E-656564454649
start=      131072, size=       20.4G, type=4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709, attrs=GUID:55
start=   232243200, size=    17825792, type=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7, name="Basic data partition"
        '''.strip().encode('utf-8')  # noqa: E501

        self._go(disk_size_bytes, partition_table, bd_pre='p4', bd_post='p4')

    @needs_root
    def test_preserves_basic_data_swap(self):
        '''
        This disk is big, so we should create a swap partition just before the
        trailing NTFS partition, and format the swap partition as swap -- but
        leave the NTFS partition alone.
        '''

        disk_size_bytes = 256071351296
        partition_table = '''
label: gpt
unit: sectors

start=        2048, size=      126976, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B
start=      129024, size=        2048, type=21686148-6449-6E6F-744E-656564454649
start=      131072, size=       20.4G, type=4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709, attrs=GUID:55
start=   482312879, size=    17825792, type=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7, name="Basic data partition"
        '''.strip().encode('utf-8')  # noqa: E501

        self._go(disk_size_bytes, partition_table,
                 bd_pre='p4', bd_post='p5', swap='p4')

    def _go(self, disk_size_bytes, partition_table,
            bd_pre=None, bd_post=None, swap=None):
        with tempfile.NamedTemporaryFile() as img:
            img.truncate(disk_size_bytes)
            sfdisk(img.name, partition_table)

            with losetup(img.name) as img_device:
                try:
                    if bd_pre is not None:
                        bd_partition = img_device + bd_pre
                        check_call(['mkfs.ntfs', '-Q', bd_partition])
                        udevadm_settle()
                        self.assert_fstype(bd_partition, 'ntfs')

                    root = img_device + 'p3'
                    check_call(["/bin/sh", "-x", ENDLESS_REPARTITION_SH, root])
                    partprobe(img_device)
                    udevadm_settle()

                    if bd_post is not None:
                        self.assert_fstype(img_device + bd_post, 'ntfs')

                    if swap is not None:
                        self.assert_fstype(img_device + swap, 'swap')
                except:
                    # Log the current state to aid debugging
                    check_call(["sfdisk", "--dump", img_device])
                    check_call(["lsblk", "-o", "+fstype", img_device])
                    # Pause
                    # check_call(["cat"])
                    raise
