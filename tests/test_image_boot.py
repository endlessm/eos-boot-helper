#!/usr/bin/python3
'''
Must be run as a user privileged enough to run
`losetup`. If run as an unprivileged user, all tests are skipped.
'''

import contextlib
import os
import tempfile
import shutil
import subprocess

from .util import (
    BaseTestCase,
    dracut_script,
    get_lsblk_field,
    losetup,
    mount,
    needs_root,
    sfdisk,
    udevadm_settle,
)

EOS_IMAGE_BOOT_SETUP = dracut_script('image-boot', 'eos-image-boot-setup')


class ImageTestCase(BaseTestCase):
    '''Base class for image-boot tests.'''
    @contextlib.contextmanager
    def make_host_device(self, filesystem):
        '''Yields the path to a temporary loopback device, formatted as
        'filesystem' by running 'mkfs', to host test image files.'''
        mkfs = 'mkfs.{}'.format(filesystem)
        with tempfile.NamedTemporaryFile() as host_img:
            host_img.truncate(4 * 1024 * 1024)
            sfdisk(host_img.name, b'start=64KiB, type=0x07')

            with losetup(host_img.name) as host_disk:
                host_device = host_disk + 'p1'
                subprocess.check_call([mkfs, host_device])

                # Wait for udev to probe new filesystem type
                udevadm_settle()

                self.assert_fstype(host_device, filesystem)
                yield host_device

    def assert_readonly(self, device, readonly):
        self.assertEqual(
            get_lsblk_field(device, 'ro'),
            '1' if readonly else '0')


class TestImageBootSetup(ImageTestCase):
    '''Tests entire eos-image-boot-setup script.'''
    def setUp(self):
        super().setUp()

        self.tmpdir = tempfile.mkdtemp()
        self.endless_img = os.path.join(self.tmpdir, 'endless.img')

        with open(self.endless_img, 'wb') as f:
            f.truncate(1 * 1024 * 1024)
            sfdisk(f.name,
                   b'start=64KiB, type=4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709',
                   label='gpt')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _mkisofs(self, *contents):
        endless_iso = os.path.join(self.tmpdir, 'endless.iso')
        subprocess.check_call((
            'xorriso', '-as', 'mkisofs',
            '-o', endless_iso,
        ) + contents)
        return endless_iso

    def _mksquashfs(self, *contents):
        endless_squash = os.path.join(self.tmpdir, 'endless.squash')
        subprocess.check_call(('mksquashfs',) + contents + (endless_squash,))
        return endless_squash

    @needs_root
    def test_image_boot_iso(self):
        '''Tests ISO > uncompressed image'''
        iso = self._mkisofs(self.endless_img)
        with losetup(iso) as host_device:
            self._go(host_device, 'endless.img', readonly=True)

    @needs_root
    def test_image_boot_iso_squashfs(self):
        '''Tests ISO > SquashFS > uncompressed image'''
        iso = self._mkisofs(self._mksquashfs(self.endless_img))
        with losetup(iso) as host_device:
            self._go(host_device, 'endless.squash', readonly=True)

    @needs_root
    def test_image_boot_exfat(self):
        '''Tests exFAT > uncompressed image'''
        with self.make_host_device('exfat') as host_device:
            with mount(host_device) as host_mount:
                shutil.copyfile(self.endless_img, host_mount + '/endless.img')

            self._go(host_device, 'endless.img', readonly=False)

    @needs_root
    def test_image_boot_exfat_squashfs(self):
        '''Tests exFAT > SquashFS > uncompressed image'''
        endless_squash = self._mksquashfs(self.endless_img)
        with self.make_host_device('exfat') as host_device:
            with mount(host_device) as host_mount:
                shutil.copyfile(endless_squash, host_mount + '/endless.squash')

            self._go(host_device, 'endless.squash', readonly=True)

    @needs_root
    def test_image_boot_ntfs(self):
        '''Tests NTFS > uncompressed image'''
        with self.make_host_device('ntfs') as host_device:
            with mount(host_device) as host_mount:
                shutil.copyfile(self.endless_img, host_mount + '/endless.img')

            self._go(host_device, 'endless.img', readonly=False)

    def _detach_if_exists(self, image):
        if os.path.exists(image):
            dev = subprocess.check_output((
                'losetup', '--output', 'NAME', '--noheadings',
                '--associated', image,
            ))
            subprocess.call(('losetup', '--detach', dev.strip()))
            subprocess.call(('blockdev', '--setrw', dev.strip()))

    def _go(self, host_device, image_path, readonly=False):
        mapped_dev = '/dev/disk/endless-image'
        mapped_part = '/dev/disk/endless-image1'

        try:
            args = [EOS_IMAGE_BOOT_SETUP, host_device, image_path]
            if readonly:
                args.insert(1, '--readonly')
            subprocess.check_call(args)
            udevadm_settle()
            self.assertTrue(os.path.exists(mapped_dev))
            self.assert_readonly(mapped_dev, readonly)
            self.assertTrue(os.path.exists(mapped_part))
            self.assert_readonly(mapped_part, readonly)
            # We could be more zealous about checking the contents of the
            # mapped partition, but TestMapImageFile -- plus the fact the
            # partition was found within the device -- is good enough.
        finally:
            # This cleanup is all best-effort and reliant on implementation
            # details of eos-image-boot-setup, whose effects are not really
            # intended to be undone -- in normal use, the mapped OS image and
            # everything behind it must exist until the machine is shut down.
            subprocess.call(('blockdev', '--setrw', host_device))
            subprocess.call(('partx', '-d', '-v', mapped_dev))

            self._detach_if_exists('/squash/endless.img')
            if os.path.exists('/squash'):
                subprocess.call(('umount', '/squash'))
                os.rmdir(('/squash'))

            self._detach_if_exists('/outer_image/endless.squash')
            self._detach_if_exists('/outer_image/endless.img')

            if os.path.exists('/outer_image'):
                subprocess.call(('umount', '/outer_image'))
                os.rmdir('/outer_image')
