import contextlib
import importlib.machinery
import importlib.util
import os
import subprocess
import tempfile
import unittest


run_needs_root_tests = bool(os.environ.get('EBH_ROOT_TESTS'))
needs_root = unittest.skipIf(not run_needs_root_tests,
                             "needs root; set EBH_ROOT_TESTS=1 to enable")


def built_program(program):
    '''Gets the absolute path to a built program in the top level of this
    repository.

    This uses the ABS_TOP_BUILDDIR environment variable to find the top build
    directory. Otherwise it falls back to system_script, which uses the top
    source directory.
    '''
    abs_top_builddir = os.environ.get('ABS_TOP_BUILDDIR')
    if abs_top_builddir:
        return os.path.join(abs_top_builddir, program)
    return system_script(program)


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
def mount(device):
    '''Mounts device on a freshly-created mount point.'''
    with tempfile.TemporaryDirectory() as mount_point:
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
    def setUp(self):
        super().setUp()

        os.environ["LANG"] = "C.UTF-8"

    def assert_fstype(self, partition, type_):
        '''Asserts that 'partition' contains a 'type_' filesystem.'''
        msg = 'expected {} to have type {!r}'.format(partition, type_)
        self.assertEqual(fstype(partition), type_, msg=msg)


def import_script_as_module(module_name, filename):
    # Import script as a module, despite its filename not being a legal module name
    spec = importlib.util.spec_from_loader(
        module_name,
        importlib.machinery.SourceFileLoader(
            module_name, system_script(filename)
        ),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def relative_link(src, dst):
    """Create a relative symbolic link pointing to src named dst."""
    if not os.path.isabs(src):
        raise ValueError(f'Source path "{src}" must be absolute')
    if not os.path.isabs(dst):
        raise ValueError(f'Destination path "{dst}" must be absolute')
    dstdir = os.path.dirname(dst)
    target = os.path.relpath(src, dstdir)
    os.makedirs(dstdir, exist_ok=True)
    os.symlink(target, dst)
