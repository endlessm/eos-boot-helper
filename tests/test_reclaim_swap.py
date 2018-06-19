#!/usr/bin/env python3
'''
Tests eos-reclaim-swap. Must be run as a user privileged enough to run
`losetup`, `swapon` and `swapoff`. If run as an unprivileged user, all tests
are skipped.
'''
from subprocess import check_call
import tempfile

from .util import (
    BaseTestCase,
    get_partition_size,
    system_script,
    losetup,
    needs_root,
    sfdisk,
    udevadm_settle,
)


EOS_RECLAIM_SWAP = system_script('eos-reclaim-swap')


class TestReclaimSwap(BaseTestCase):

    @needs_root
    def test_noop_if_no_swap(self):
        '''
        If there is no swap partition this service should do nothing.
        '''
        disk_size_bytes = 256071351296
        partition_table = '''
label: gpt
unit: sectors

start=        2048, size=      126976, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B
start=      129024, size=        2048, type=21686148-6449-6E6F-744E-656564454649
start=      131072, size=       20.4G, type=4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709
        '''.strip().encode('utf-8')  # noqa: E501

        self._go(disk_size_bytes, partition_table)

    @needs_root
    def test_remove_swap_partition(self):
        '''
        If the swap partition is located right after the root partition it
        should be removed and the root partition should be expanded to make use
        of the new availble space.
        '''
        disk_size_bytes = 256071351296
        partition_table = '''
label: gpt
unit: sectors

start=        2048, size=      126976, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B
start=      129024, size=        2048, type=21686148-6449-6E6F-744E-656564454649
start=      131072, size=   473794560, type=4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709
start=   473925632, size=     8387247, type=0657FD6D-A4AB-43C4-84E5-0933C84B4F4F
        '''.strip().encode('utf-8')  # noqa: E501

        self._go(disk_size_bytes, partition_table, swap='p4')

    @needs_root
    def test_remove_swap_partition_preserving_anything_after_it(self):
        '''
        If the swap partition is located right after the root partition it
        should be removed and the root partition should be expanded to make use
        of the new availble space. Any other partition after the swap partition
        (normally an OEM recovery partition) should be preserved.
        '''
        disk_size_bytes = 256071351296
        partition_table = '''
label: gpt
unit: sectors

start=        2048, size=      126976, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B
start=      129024, size=        2048, type=21686148-6449-6E6F-744E-656564454649
start=      131072, size=   473794560, type=4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709
start=   473925632, size=     8387247, type=0657FD6D-A4AB-43C4-84E5-0933C84B4F4F
start=   482312879, size=    17825792, type=EBD0A0A2-B9E5-4433-87C0-68B6B72699C7, name="Basic data partition"
        '''.strip().encode('utf-8')  # noqa: E501

        self._go(disk_size_bytes, partition_table, bd_pre='p5', bd_post='p4',
                 swap='p4')

    def _go(self, disk_size_bytes, partition_table, bd_pre=None, bd_post=None,
            swap=None):

        with tempfile.NamedTemporaryFile() as img:
            img.truncate(disk_size_bytes)
            sfdisk(img.name, partition_table)

            with losetup(img.name) as img_device:
                try:
                    swap_start = None

                    if bd_pre is not None:
                        bd_partition = img_device + bd_pre
                        check_call(['mkfs.ntfs', '-Q', bd_partition])
                        udevadm_settle()
                        self.assert_fstype(bd_partition, 'ntfs')

                    if swap is not None:
                        swap_partition = img_device + swap
                        swap_pnum = int(swap[1:])
                        check_call(['mkswap', swap_partition])
                        self.assert_fstype(swap_partition, 'swap')
                        check_call(['swapon', swap_partition])
                        swap_size = get_partition_size(img_device, swap_pnum)

                    root = img_device + 'p3'
                    root_size = get_partition_size(img_device, 3)

                    check_call(['mke2fs', '-t', 'ext4',
                        '-O', 'dir_index,^huge_file', '-m1', '-L', 'ostree',
                        '-T', 'default', root ])
                    self.assert_fstype(swap_partition, 'ext4')

                    check_call([EOS_RECLAIM_SWAP, root])
                    udevadm_settle()

                    if bd_post is not None:
                        self.assert_fstype(img_device + bd_post, 'ntfs')

                    if swap is not None:
                        self.assert_not_fstype(img_device + bd_post, 'swap')
                        self.assert_partition_size(root, root_size + swap_size)

                except:
                    # Log the current state to aid debugging
                    check_call(["sfdisk", "--dump", img_device])
                    check_call(["lsblk", "-o", "+fstype", img_device])
                    raise
