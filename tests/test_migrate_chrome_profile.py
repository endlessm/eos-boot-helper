#!/usr/bin/python3
"""
Tests eos-migrate-chrome-profile

This test is based on test_migrate_chromium_profile.py.
"""

import tempfile
import textwrap
import os

from .util import BaseTestCase, system_script, import_script_as_module

emfp = import_script_as_module("emfp", system_script("eos-migrate-chrome-profile"))


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
            text/html=google-chrome.desktop
            image/jpeg=eog.desktop

            [Added Associations]
            text/xml=google-chrome.desktop;org.mozilla.firefox.desktop;org.chromium.Chromium.desktop;
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
            text/html=com.google.Chrome.desktop;
            image/jpeg=eog.desktop

            [Added Associations]
            text/xml=com.google.Chrome.desktop;org.mozilla.firefox.desktop;org.chromium.Chromium.desktop;
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


class TestUpdateDesktopShortcuts(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_shortcuts_dir(self):
        emfp.update_desktop_shortcuts(os.path.join(self.tmp.name, "no-such-directory"))

    def test_empty_shortcuts_dir(self):
        emfp.update_desktop_shortcuts(self.tmp.name)

    def test_not_there(self):
        orig_data = textwrap.dedent(
            """
            [Desktop Entry]
            Exec=/usr/bin/chromium-browser --profile-directory=Default
            """
        ).lstrip()
        expected_data = orig_data

        self._test(orig_data, expected_data)

    def test_there(self):
        orig_data = textwrap.dedent(
            """
            #!/usr/bin/env xdg-open
            [Desktop Entry]
            Version=1.0
            Terminal=false
            Type=Application
            Name=YouTube
            Exec=/usr/bin/eos-google-chrome "--profile-directory=Profile 1"
            Icon=chrome-agimnkijcaahngcdmfeangaknmldooml-Profile_1
            StartupWMClass=crx_agimnkijcaahngcdmfeangaknmldooml
            Actions=Explore;Subscriptions

            [Desktop Action Explore]
            Name=Explore
            Exec=/usr/bin/eos-google-chrome "--profile-directory=Profile 1"

            [Desktop Action Subscriptions]
            Name=Subscriptions
            Exec=/usr/bin/eos-google-chrome "--profile-directory=Profile 1"
            """
        ).lstrip()
        expected_data = textwrap.dedent(
            """
            #!/usr/bin/env xdg-open
            [Desktop Entry]
            Version=1.0
            Terminal=false
            Type=Application
            Name=YouTube
            Exec=/usr/bin/flatpak run com.google.Chrome "--profile-directory=Profile 1"
            Icon=chrome-agimnkijcaahngcdmfeangaknmldooml-Profile_1
            StartupWMClass=crx_agimnkijcaahngcdmfeangaknmldooml
            Actions=Explore;Subscriptions

            [Desktop Action Explore]
            Name=Explore
            Exec=/usr/bin/flatpak run com.google.Chrome "--profile-directory=Profile 1"

            [Desktop Action Subscriptions]
            Name=Subscriptions
            Exec=/usr/bin/flatpak run com.google.Chrome "--profile-directory=Profile 1"
            """
        ).lstrip()

        self._test(orig_data, expected_data)

    def test_multi_languages(self):
        orig_data = textwrap.dedent(
            """
            # Comment
            [Desktop Entry]
            Name=Chrome
            Name[en_GB]=Chrome, milord
            Exec=/usr/bin/eos-google-chrome --profile-directory=Default
            """
        ).lstrip()
        expected_data = textwrap.dedent(
            """
            # Comment
            [Desktop Entry]
            Name=Chrome
            Name[en_GB]=Chrome, milord
            Exec=/usr/bin/flatpak run com.google.Chrome --profile-directory=Default
            """
        ).lstrip()

        self._test(orig_data, expected_data)

    def test_no_exec_in_group(self):
        orig_data = textwrap.dedent(
            """
            [Dummy Group]
            foo=bar
            """
        ).lstrip()
        expected_data = orig_data

        self._test(orig_data, expected_data)

    def _test(self, orig_data, expected_data):
        test_desktop = os.path.join(self.tmp.name,
                                    "test.desktop")
        with open(test_desktop, "w") as f:
            f.write(orig_data)

        emfp.update_desktop_shortcuts(self.tmp.name)
        with open(test_desktop, "r") as f:
            new_data = f.read()

        self.assertEqual(expected_data, new_data)


class TestUpdateOldConfigReferences(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_nonexistent(self):
        emfp.update_mimeapps_list(os.path.join(self.tmp.name, "mimeapps.list"))

    def test_not_there(self):
        orig_data = ""
        expected_data = orig_data

        self._test(orig_data, expected_data)

    def test_there_system(self):
        orig_data = '{"Path":"/usr/lib/google-chrome/WidevineCdm"}'
        expected_data = '{"Path":""}'

        self._test(orig_data, expected_data)

    def test_there_local(self):
        user_home_dir = os.path.expanduser("~/")
        orig_data = \
            '{"Path":"' + user_home_dir + \
            '.config/google-chrome/WidevineCdm/4.10.1610.0"}'
        expected_data = \
            '{"Path":"' + user_home_dir + \
            '.var/app/com.google.Chrome/config/google-chrome/WidevineCdm/4.10.1610.0"}'

        self._test(orig_data, expected_data)

    def _test(self, orig_data, expected_data):
        last_updated_widevine = os.path.join(self.tmp.name,
                                             "latest-component-updated-widevine-cdm")
        with open(last_updated_widevine, "w") as f:
            f.write(orig_data)

        emfp.update_old_config_references(last_updated_widevine)
        with open(last_updated_widevine, "r") as f:
            new_data = f.read()

        self.assertEqual(expected_data, new_data)
