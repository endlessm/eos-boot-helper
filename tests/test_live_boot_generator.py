#!/usr/bin/python3
'''Exercises eos-live-boot-generator for the live and !live cases.'''

import os
import subprocess
import unittest
from tempfile import TemporaryDirectory
from .util import system_script


EOS_LIVE_BOOT_GENERATOR = system_script('eos-live-boot-generator')


class TestLiveBootGenerator(unittest.TestCase):
    '''Exercises eos-live-boot-generator for the live and !live cases.'''
    def test_is_live(self):
        '''Test with endless.live_boot on cmdline.'''
        with TemporaryDirectory() as tmpdir:
            settle_link = self._go(tmpdir, b'abc endless.live_boot def')
            self.assertTrue(os.path.islink(settle_link))

    def test_not_live(self):
        '''Test with endless.live_boot not on cmdline.'''
        with TemporaryDirectory() as tmpdir:
            settle_link = self._go(tmpdir, b'abc def')
            self.assertFalse(os.path.exists(settle_link))

    def test_wrong_live(self):
        '''Test with endless.live_boot not strictly on cmdline.'''
        with TemporaryDirectory() as tmpdir:
            settle_link = self._go(tmpdir, b'abc xendless.live_bootleg def')
            self.assertFalse(os.path.exists(settle_link))

    def _go(self, tmpdir, cmdline):
        proc_cmdline = os.path.join(tmpdir, 'cmdline')
        with open(proc_cmdline, 'wb') as f:
            f.write(cmdline)

        subprocess.check_call(['sh', '-x', EOS_LIVE_BOOT_GENERATOR, tmpdir],
                              env={'proc_cmdline': proc_cmdline})

        return os.path.join(tmpdir,
                            'local-fs.target.wants',
                            'systemd-udev-settle.service')
