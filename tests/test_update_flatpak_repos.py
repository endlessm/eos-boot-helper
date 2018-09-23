#!/usr/bin/python3
"""
Tests eos-update-flatpak-repos
"""

import importlib.util
import importlib.machinery
import tempfile
import textwrap

from .util import BaseTestCase, system_script
import gi

gi.require_version("OSTree", "1.0")
from gi.repository import Gio, OSTree  # noqa: E402


# Import script as a module, despite its filename not being a legal module name
spec = importlib.util.spec_from_loader(
    "eufr",
    importlib.machinery.SourceFileLoader(
        "eufr", system_script("eos-update-flatpak-repos")
    ),
)
eufr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eufr)


class TestMangleDesktopFile(BaseTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _ensure_dirs(self, mtree, *dirs):
        for name in dirs:
            _, mtree = mtree.ensure_dir(name)
        return mtree

    def test_rename_main_desktop(self):
        orig_name = "com.example.Hello.desktop"
        orig_data = textwrap.dedent(
            """
            [Desktop Entry]
            DBusActivatable=true
            Icon=com.example.Hello
            X-Flatpak-RenamedFrom=net.example.Howdy.desktop;
            """
        ).strip()

        expected_name = "org.example.Hi.desktop"
        expected_data = textwrap.dedent(
            """
            [Desktop Entry]
            Icon=org.example.Hi
            X-Flatpak-RenamedFrom=net.example.Howdy.desktop;com.example.Hello.desktop;
            """
        ).strip()

        self._test(orig_name, orig_data, expected_name, expected_data)

    def test_rename_extra_desktop(self):
        orig_name = "com.example.Hello.Again.desktop"
        orig_data = textwrap.dedent(
            """
            [Desktop Entry]
            Icon=com.example.Hello.Next
            """
        ).strip()

        expected_name = "org.example.Hi.Again.desktop"
        expected_data = textwrap.dedent(
            """
            [Desktop Entry]
            Icon=org.example.Hi.Next
            X-Flatpak-RenamedFrom=com.example.Hello.Again.desktop;
            """
        ).strip()

        self._test(orig_name, orig_data, expected_name, expected_data)

    def _test(self, orig_name, orig_data, expected_name, expected_data):
        repo = OSTree.Repo.new(Gio.File.new_for_path(self.tmp.name))
        repo.set_disable_fsync(True)
        repo.create(OSTree.RepoMode.BARE_USER_ONLY)

        mtree = OSTree.MutableTree()

        # Store the original file in the tree
        data_bytes = orig_data.encode("utf-8")
        stream = Gio.MemoryInputStream.new_from_data(data_bytes)
        info = Gio.FileInfo()
        info.set_size(len(data_bytes))
        info.set_name(orig_name)

        _, export = mtree.ensure_dir("export")
        _, share = export.ensure_dir("share")
        _, apps = share.ensure_dir("applications")
        eufr.mtree_add_file(repo, apps, stream, info)

        # Rename the contents of the export/ directory
        eufr.rename_exports(repo, export, "com.example.Hello", "org.example.Hi")

        # Check the applications/ subdirectory is as we expect
        files = apps.get_files()
        self.assertEqual(list(files.keys()), [expected_name])
        _, stream, info, _ = repo.load_file(files[expected_name])
        bytes_ = stream.read_bytes(info.get_size())
        self.assertEqual(bytes_.get_data().decode("utf-8").strip(), expected_data)
