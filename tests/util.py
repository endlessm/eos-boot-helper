import contextlib
import subprocess
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


def fstype(device):
    return subprocess.check_output([
        'lsblk', '--noheading', '--output', 'fstype', device
    ]).decode('utf-8').strip()


def sfdisk(device, partition_table):
    args = ("sfdisk", device)
    sfdisk_proc = subprocess.Popen(args, stdin=subprocess.PIPE)
    sfdisk_proc.communicate(partition_table)
    if sfdisk_proc.returncode:
        raise subprocess.CalledProcessError(sfdisk_proc.returncode, args)


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
