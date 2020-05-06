#!/usr/bin/python3
"""
Tests eos-migrate-firefox-profile
"""

import tempfile
import textwrap
import os

from .util import BaseTestCase, system_script, import_script_as_module

emfp = import_script_as_module("emfp", system_script("eos-migrate-firefox-profile"))


class TestMangleMetadataAndDesktopFile(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_copy_endless_install_section(self):
        orig_data = textwrap.dedent(
            """
            [Profile1]
            Name=default
            IsRelative=1
            Path=lgcq05lh.default
            Default=1

            [Profile0]
            Name=default-release
            IsRelative=1
            Path=x4p6znk4.default-release

            [General]
            StartWithLastProfile=1
            Version=2

            [InstallFF6C2EBF42BF07E5]
            Default=x4p6znk4.default-release
            Locked=1
            """
        ).lstrip()
        expected_data = textwrap.dedent(
            """
            [Profile1]
            Name=default
            IsRelative=1
            Path=lgcq05lh.default
            Default=1

            [Profile0]
            Name=default-release
            IsRelative=1
            Path=x4p6znk4.default-release

            [General]
            StartWithLastProfile=1
            Version=2

            [InstallFF6C2EBF42BF07E5]
            Default=x4p6znk4.default-release
            Locked=1

            [InstallCF146F38BCAB2D21]
            Default=x4p6znk4.default-release
            Locked=1
            """
        ).lstrip()

        self._test(orig_data, expected_data)

    def test_no_action_if_no_endless_section(self):
        orig_data = ""
        expected_data = ""
        self._test(orig_data, expected_data)

    def test_no_action_if_mozilla_section_exists(self):
        orig_data = textwrap.dedent(
            """
            [Profile1]
            Name=default
            IsRelative=1
            Path=lgcq05lh.default
            Default=1

            [Profile0]
            Name=default-release
            IsRelative=1
            Path=x4p6znk4.default-release

            [General]
            StartWithLastProfile=1
            Version=2

            [InstallFF6C2EBF42BF07E5]
            Default=x4p6znk4.default-release
            Locked=1

            [InstallCF146F38BCAB2D21]
            Default=lgcq05lh.default
            Locked=1
            """
        ).lstrip()
        expected_data = orig_data

        self._test(orig_data, expected_data)

    def _test(self, orig_data, expected_data):
        profiles_ini = os.path.join(self.tmp.name, "profiles.ini")
        with open(profiles_ini, "w") as f:
            f.write(orig_data)

        emfp.copy_install_section(profiles_ini)
        with open(profiles_ini, "r") as f:
            new_data = f.read()

        self.assertEqual(expected_data, new_data)
