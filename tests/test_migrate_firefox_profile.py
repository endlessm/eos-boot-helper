#!/usr/bin/python3
"""
Tests eos-migrate-firefox-profile
"""

import tempfile
import textwrap
import os

from .util import BaseTestCase, system_script, import_script_as_module

emfp = import_script_as_module("emfp", system_script("eos-migrate-firefox-profile"))


class TestUpdateMimeappsList(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_nonexistent(self):
        emfp.update_mimeapps_list(os.path.join(self.tmp.name, "mimeapps.list"))

    def test_not_there(self):
        orig_data = textwrap.dedent(
            """
            [Default Applications]
            image/jpeg=eog.desktop
            """
        ).lstrip()
        expected_data = orig_data

        self._test(orig_data, expected_data)

    def test_there(self):
        orig_data = textwrap.dedent(
            """
            [Default Applications]
            text/html=org.mozilla.Firefox.desktop
            image/jpeg=eog.desktop

            [Added Associations]
            text/xml=google-chrome.desktop;org.mozilla.Firefox.desktop;chromium-browser.desktop;
            """
        ).lstrip()
        """
        The trailing semicolon in the [Default Applications] text/html entry is legal.

        https://specifications.freedesktop.org/mime-apps-spec/latest/ar01s03.html says:

            The value is a semicolon-separated list of desktop file IDs (as defined in
            the desktop entry spec).

        https://specifications.freedesktop.org/desktop-entry-spec/latest/ar01s04.html
        says:

            The multiple values should be separated by a semicolon and the value of the
            key may be optionally terminated by a semicolon.

        GKeyFile always adds the semicolon. What's fun is that when GLib itself updates
        [Default Applications], it uses set_string() rather than set_string_list(), even
        though it parses these as lists.
        """
        expected_data = textwrap.dedent(
            """
            [Default Applications]
            text/html=org.mozilla.firefox.desktop;
            image/jpeg=eog.desktop

            [Added Associations]
            text/xml=google-chrome.desktop;org.mozilla.firefox.desktop;chromium-browser.desktop;
            """
        ).lstrip()

        self._test(orig_data, expected_data)

    def _test(self, orig_data, expected_data):
        mimeapps_list = os.path.join(self.tmp.name, "mimeapps.list")
        with open(mimeapps_list, "w") as f:
            f.write(orig_data)

        emfp.update_mimeapps_list(mimeapps_list)
        with open(mimeapps_list, "r") as f:
            new_data = f.read()

        self.assertEqual(expected_data, new_data)


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
