import contextlib
import subprocess
import tempfile
import unittest
import os


def dracut_script(module, script):
    '''Gets the absolute path to a script in a dracut module in this
    repository.'''
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '../dracut',
            module,
            script))


def partprobe(device):
    subprocess.check_call(['partprobe', device])


def udevadm_settle():
    subprocess.check_call(['udevadm', 'settle'])


def get_lsblk_field(device, field):
    return subprocess.check_output([
        'lsblk', '--nodeps', '--noheading', '--output', field, device
    ]).decode('utf-8').strip()


def fstype(device):
    return get_lsblk_field(device, 'fstype')


def sfdisk(device, partition_table, label='dos'):
    args = ("sfdisk", "--label", label, device)
    sfdisk_proc = subprocess.Popen(args, stdin=subprocess.PIPE)
    sfdisk_proc.communicate(partition_table)
    if sfdisk_proc.returncode:
        raise subprocess.CalledProcessError(sfdisk_proc.returncode, args)


@contextlib.contextmanager
def mount(device):
    '''Mounts device on a freshly-created mount point.'''
    mount_point = tempfile.mkdtemp()
    try:
        subprocess.check_call(['mount', device, mount_point])

        try:
            yield mount_point
        finally:
            subprocess.check_call(['umount', mount_point])
    finally:
        os.rmdir(mount_point)


class BaseTestCase(unittest.TestCase):
    @contextlib.contextmanager
    def losetup(self, path):
        '''Yields a loopback device for path.'''
        try:
            args = ('losetup', '--find', '--show', path,)
            output = subprocess.check_output(args)
        except subprocess.CalledProcessError:
            self.skipTest(reason='losetup failed (not running as root?)')

        device = output.decode('utf-8').strip()
        try:
            partprobe(device)
            yield device
        finally:
            subprocess.check_call(['losetup', '--detach', device])

    def assert_fstype(self, partition, type_):
        '''Asserts that 'partition' contains a 'type_' filesystem.'''
        msg = 'expected {} to have type {!r}'.format(partition, type_)
        self.assertEqual(fstype(partition), type_, msg=msg)
