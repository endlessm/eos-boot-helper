import contextlib
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
        subprocess.call(['partx', '-a', device])
        udevadm_settle()
        yield device
    finally:
        subprocess.call(['partx', '-d', device])
        subprocess.check_call(['losetup', '--detach', device])
        udevadm_settle()


class BaseTestCase(unittest.TestCase):
    def assert_fstype(self, partition, type_):
        '''Asserts that 'partition' contains a 'type_' filesystem.'''
        msg = 'expected {} to have type {!r}'.format(partition, type_)
        self.assertEqual(fstype(partition), type_, msg=msg)
