import contextlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest


run_needs_root_tests = bool(os.environ.get('EBH_ROOT_TESTS'))
needs_root = unittest.skipIf(not run_needs_root_tests,
                             "needs root; set EBH_ROOT_TESTS=1 to enable")


def system_script(script):
    '''Gets the absolute path to a script in the top level of this
    repository.'''
    return os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', script))


def dracut_script(module, script):
    '''Gets the absolute path to a script in a dracut module in this
    repository.'''
    return system_script(os.path.join('dracut', module, script))


def partprobe(device):
    subprocess.check_call(['partprobe', device])


def udevadm_settle():
    subprocess.check_call(['udevadm', 'settle'])


def get_lsblk_field(device, field):
    return subprocess.check_output([
        'lsblk', '--nodeps', '--noheading', '--output', field, device
    ], stderr=subprocess.PIPE).decode('utf-8').strip()


def fstype(device):
    return get_lsblk_field(device, 'fstype')


def sfdisk(device, partition_table, label='dos'):
    args = ("sfdisk", "--label", label, device)
    sfdisk_proc = subprocess.Popen(args, stdin=subprocess.PIPE)
    sfdisk_proc.communicate(partition_table)
    if sfdisk_proc.returncode:
        raise subprocess.CalledProcessError(sfdisk_proc.returncode, args)


def get_partition_size(device, partnum):
     disk_info = json.loads(subprocess.check_output(["sfdisk", "--json", device]))
     return disk_info["partitiontable"]["partitions"][partnum-1]["size"]


@contextlib.contextmanager
def TemporaryDirectory():
    '''Reimplementation of tempfile.TemporaryDirectory from Python >= 3.5
    since Endless OS only has Python 3.4.'''
    d = tempfile.mkdtemp()
    try:
        yield d
    finally:
        shutil.rmtree(d)


@contextlib.contextmanager
def mount(device):
    '''Mounts device on a freshly-created mount point.'''
    with TemporaryDirectory() as mount_point:
        subprocess.check_call(['mount', device, mount_point])

        try:
            yield mount_point
        finally:
            subprocess.check_call(['umount', mount_point])


@contextlib.contextmanager
def losetup(path):
    '''Yields a loopback device for path.'''
    args = ('losetup', '--find', '--show', path,)
    output = subprocess.check_output(args)

    device = output.decode('utf-8').strip()
    try:
        partprobe(device)
        yield device
    finally:
        subprocess.check_call(['losetup', '--detach', device])


class BaseTestCase(unittest.TestCase):
    def assert_fstype(self, partition, type_):
        '''Asserts that 'partition' contains a 'type_' filesystem.'''
        msg = 'expected {} to have type {!r}'.format(partition, type_)
        self.assertEqual(fstype(partition), type_, msg=msg)

    def assert_not_fstype(self, partition, type_):
        '''Asserts that if partition exists it 'partition' does not contain a
        'type_' filesystem.'''
        msg = 'expected {} to not exist or not have type {!r}'.format(partition, type_)
        try:
            fs = fstype(partition)
        except subprocess.CalledProcessError as e:
            if (e.args[0] == 32):
                return True
            else:
                raise
        self.assertNotEqual(fs, type_, msg=msg)

    def assert_partition_size(self, partition, size):
        '''Asserts that 'partition' size is 'size' sectors long.'''
        msg = 'expected {} to have type {!r}'.format(partition, size)
        psize = get_partition_size(img_device, int(partition[-1:]))
        self.assertEqual(psize, size, msg=msg)
