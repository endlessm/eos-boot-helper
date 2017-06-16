#!/usr/bin/env python3
'''
Tests endless-repartition.sh. Must be run as a user privileged enough to run
`losetup`. If run as an unprivileged user, all tests are skipped.
'''
import contextlib
import os
import subprocess
import tempfile
import unittest


ENDLESS_REPARTITION_SH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        '../dracut/repartition/endless-repartition.sh'))


def partprobe(device):
    subprocess.check_call(['partprobe', device])


def udevadm_settle():
    subprocess.check_call(['udevadm', 'settle'])


def fstype(device):
    return subprocess.check_output([
        'lsblk', '--noheading', '--output', 'fstype', device
    ]).decode('utf-8').strip()


class TestRepartition(unittest.TestCase):
    @contextlib.contextmanager
    def losetup(self, path):
        try:
            output = subprocess.check_output(['losetup', '--find', '--show', path])
        except subprocess.CalledProcessError:
            self.skipTest(reason='losetup failed (not running as root?)')

        device = output.decode('utf-8').strip()
        try:
            partprobe(device)
            yield device
        finally:
            subprocess.check_call(['losetup', '--detach', device])

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
        '''.strip().encode('utf-8')

        self._go(disk_size_bytes, partition_table, swap='p4')

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
        '''.strip().encode('utf-8')

        self._go(disk_size_bytes, partition_table, bd_pre='p4', bd_post='p4')

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
        '''.strip().encode('utf-8')

        self._go(disk_size_bytes, partition_table, bd_pre='p4', bd_post='p5', swap='p4')

    def _go(self, disk_size_bytes, partition_table, bd_pre=None, bd_post=None, swap=None):
        with tempfile.NamedTemporaryFile() as img:
            img.truncate(disk_size_bytes)
            sfdisk = subprocess.Popen(["sfdisk", img.name], stdin=subprocess.PIPE)
            sfdisk.communicate(partition_table)
            self.assertEqual(sfdisk.returncode, 0, 'sfdisk failed')

            with self.losetup(img.name) as img_device:
                try:
                    if bd_pre is not None:
                        bd_partition = img_device + bd_pre
                        subprocess.check_call(['mkfs.ntfs', '-Q', bd_partition])
                        udevadm_settle()
                        self.assert_fstype(bd_partition, 'ntfs')

                    root = img_device + 'p3'
                    subprocess.check_call(["/bin/sh", "-x", ENDLESS_REPARTITION_SH, root])
                    partprobe(img_device)
                    udevadm_settle()

                    if bd_post is not None:
                        self.assert_fstype(img_device + bd_post, 'ntfs')

                    if swap is not None:
                        self.assert_fstype(img_device + swap, 'swap')
                except:
                    # Log the current state to aid debugging
                    subprocess.check_call(["sfdisk", "--dump", img_device])
                    subprocess.check_call(["lsblk", "-o", "+fstype", img_device])
                    # Pause
                    # subprocess.check_call(["cat"])
                    raise

    def assert_fstype(self, partition, type_):
        '''Asserts that 'partition' contains a 'type_' filesystem.'''
        msg = 'expected {} to have type {!r}'.format(partition, type_)
        self.assertEqual(fstype(partition), type_, msg=msg)
