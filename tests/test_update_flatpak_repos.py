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
from gi.repository import GLib, Gio, OSTree  # noqa: E402


# Import script as a module, despite its filename not being a legal module name
spec = importlib.util.spec_from_loader(
    "eufr",
    importlib.machinery.SourceFileLoader(
        "eufr", system_script("eos-update-flatpak-repos")
    ),
)
eufr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eufr)


class TestMangleMetadataAndDesktopFile(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.tmp = tempfile.TemporaryDirectory()

        self.repo = OSTree.Repo.new(Gio.File.new_for_path(self.tmp.name))
        self.repo.set_disable_fsync(True)
        self.repo.create(OSTree.RepoMode.BARE_USER_ONLY)

        self.mtree = OSTree.MutableTree()

    def tearDown(self):
        self.tmp.cleanup()

    def test_rename_empty_desktop(self):
        '''No keys we care about'''
        orig_name = "com.example.Hello.desktop"
        orig_data = textwrap.dedent(
            """
            [Desktop Entry]
            """
        ).strip()

        expected_name = "org.example.Hi.desktop"
        expected_data = textwrap.dedent(
            """
            [Desktop Entry]
            X-Flatpak-RenamedFrom=com.example.Hello.desktop;
            """
        ).strip()

        self._test_simple(orig_name, orig_data, expected_name, expected_data)

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

        self._test_simple(orig_name, orig_data, expected_name, expected_data)

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

        self._test_simple(orig_name, orig_data, expected_name, expected_data)

    def test_rename_vendor_desktop(self):
        """The Menu Specification introduces the concept of a vendor prefix. In short,
        XDG_DATA_DIR/applications/vendor/foo.desktop should be treated as if it were
        XDG_DATA_DIR/applications/vendor-foo.desktop. This concept was embraced by the
        KDE games we shipped, with a 'kde4' vendor prefix."""
        orig_id = "com.example.Hello"
        orig_data = textwrap.dedent(
            """
            [Desktop Entry]
            """
        ).strip()

        expected_id = "org.example.Hi"
        expected_name = expected_id + ".desktop"
        expected_data = textwrap.dedent(
            """
            [Desktop Entry]
            X-Flatpak-RenamedFrom=kde4-com.example.Hello.desktop;
            """
        ).strip()

        # Generate metadata file, store it in the tree
        orig_metadata = textwrap.dedent(
            """
            [Application]
            name=com.example.Hello
            runtime=org.freedesktop.Platform/x86_64/18.08
            sdk=org.freedesktop.Sdk/x86_64/18.08
            command=hello
            """
        ).strip()
        self._put_file((), "metadata", orig_metadata)

        # Store the original file in the tree
        kde4_path = ('export', 'share', 'applications', 'kde4')
        self._put_file(kde4_path, orig_id + ".desktop", orig_data)

        metadata_str, vendor_prefixes = eufr.rewrite_metadata(
            self.repo, self.mtree, "com.example.Hello", "org.example.Hi",
        )
        self.assertEqual({'kde4'}, vendor_prefixes)

        # Check the kde4/ directory is now empty. In theory we might like the migration
        # script to have deleted it, but the dangling empty directory will go away as
        # soon as the user updates to the Flathub version of the app.
        files = self._mkdir_p(kde4_path).get_files()
        self.assertEqual(list(files.keys()), [])

        # Check the applications/ subdirectory is as we expect
        desktop_path = ('export', 'share', 'applications')
        files = self._mkdir_p(desktop_path).get_files()
        self.assertEqual(list(files.keys()), [expected_name])
        _, stream, info, _ = self.repo.load_file(files[expected_name])
        bytes_ = stream.read_bytes(info.get_size())
        self.assertEqual(bytes_.get_data().decode("utf-8").strip(), expected_data)

        # Check the metadata has been updated with the new name
        self.assertEqual(self._get_name_from_metadata(), expected_id)

    def test_rename_extra_data(self):
        """Tests that the Extra Data section is stripped from the metadata."""
        orig_id = "com.example.Hello"
        expected_id = "org.example.Hi"

        # Generate metadata file, store it in the tree
        orig_metadata = textwrap.dedent(
            """
            [Application]
            name=com.example.Hello
            runtime=org.freedesktop.Platform/x86_64/18.08
            sdk=org.freedesktop.Sdk/x86_64/18.08
            command=hello

            [Extra Data]
            name=skypeforlinux-64.deb
            checksum=e017fa5f3b78104b18c9e3ec00a678e513095cd4129a83b301f2b2c0dbb606a5
            size=73441958
            uri=https://repo.skype.com/deb/pool/main/s/skypeforlinux/skypeforlinux_8.34.0.78_amd64.deb
            """
        ).strip()
        self._put_file((), "metadata", orig_metadata)

        # Pop an empty export dir in, to suppress a (legit) warning
        self._mkdir_p(('export',))

        metadata_str, vendor_prefixes = eufr.rewrite_metadata(
            self.repo, self.mtree, orig_id, expected_id,
        )
        self.assertEqual(set(), vendor_prefixes)

        # Check the metadata has been updated with the new name
        metadata = self._get_metadata()
        self.assertEqual(metadata.get_string('Application', 'name'), expected_id)

        # and that the Extra Data section has been removed
        self.assertFalse(metadata.has_group('Extra Data'))

        # TODO: test the end-to-end migration process, including copying the
        # old extra data into place

    def test_remove_extra_data(self):
        """Tests that the Extra Data section is stripped from the metadata but
        that the desktop file is left intact, even if there is no rename."""
        orig_id = "com.example.Hello"

        # Generate metadata file, store it in the tree
        orig_metadata = textwrap.dedent(
            """
            [Application]
            name=com.example.Hello
            runtime=org.freedesktop.Platform/x86_64/18.08
            sdk=org.freedesktop.Sdk/x86_64/18.08
            command=hello

            [Extra Data]
            name=skypeforlinux-64.deb
            checksum=e017fa5f3b78104b18c9e3ec00a678e513095cd4129a83b301f2b2c0dbb606a5
            size=73441958
            uri=https://repo.skype.com/deb/pool/main/s/skypeforlinux/skypeforlinux_8.34.0.78_amd64.deb
            """
        ).strip()
        self._put_file((), "metadata", orig_metadata)

        # Generate .desktop file, store it in the tree
        orig_name = orig_id + '.desktop'
        orig_desktop = textwrap.dedent(
            """
            [Desktop Entry]
            """
        ).strip()
        desktop_path = ('export', 'share', 'applications')
        self._put_file(desktop_path, orig_name, orig_desktop)

        metadata_str, vendor_prefixes = eufr.rewrite_metadata(
            self.repo, self.mtree, orig_id, orig_id,
        )
        self.assertEqual(set(), vendor_prefixes)

        # Check the metadata name is unchanged
        metadata = self._get_metadata()
        self.assertEqual(metadata.get_string('Application', 'name'), orig_id)

        # and that the Extra Data section has been removed
        self.assertFalse(metadata.has_group('Extra Data'))

        # Check the applications/ subdirectory still has the .desktop file
        files = self._mkdir_p(desktop_path).get_files()
        self.assertEqual(list(files.keys()), [orig_name])

        # and that the contents are unchanged
        _, stream, info, _ = self.repo.load_file(files[orig_name])
        bytes_ = stream.read_bytes(info.get_size())
        self.assertEqual(bytes_.get_data().decode("utf-8").strip(),
                         orig_desktop)

    def _mkdir_p(self, path):
        mtree = self.mtree
        for name in path:
            _, mtree = mtree.ensure_dir(name)
        return mtree

    def _put_file(self, parents, name, data):
        data_bytes = data.encode("utf-8")
        stream = Gio.MemoryInputStream.new_from_data(data_bytes)
        info = Gio.FileInfo()
        info.set_size(len(data_bytes))
        info.set_name(name)

        directory = self._mkdir_p(parents)
        eufr.mtree_add_file(self.repo, directory, stream, info)

    def _get_metadata(self):
        _, stream, info, _ = self.repo.load_file(self.mtree.get_files()['metadata'])
        bytes_ = stream.read_bytes(info.get_size())

        kf = GLib.KeyFile()
        kf.load_from_bytes(bytes_, GLib.KeyFileFlags.NONE)
        return kf

    def _get_name_from_metadata(self):
        return self._get_metadata().get_string('Application', 'name')

    def _test_simple(self, orig_name, orig_data, expected_name, expected_data):
        orig_id = "com.example.Hello"
        expected_id = "org.example.Hi"

        # Generate metadata file, store it in the tree
        orig_metadata = textwrap.dedent(
            """
            [Application]
            name={orig_id}
            runtime=org.freedesktop.Platform/x86_64/18.08
            sdk=org.freedesktop.Sdk/x86_64/18.08
            command=hello
            """
        ).strip().format(orig_id=orig_id)
        self._put_file((), "metadata", orig_metadata)

        # Store the original file in the tree
        desktop_path = ('export', 'share', 'applications')
        self._put_file(desktop_path, orig_name, orig_data)

        metadata_str, vendor_prefixes = eufr.rewrite_metadata(
            self.repo, self.mtree, orig_id, expected_id,
        )
        self.assertEqual(set(), vendor_prefixes)

        # Check the applications/ subdirectory is as we expect
        files = self._mkdir_p(desktop_path).get_files()
        self.assertEqual(list(files.keys()), [expected_name])
        _, stream, info, _ = self.repo.load_file(files[expected_name])
        bytes_ = stream.read_bytes(info.get_size())
        self.assertEqual(bytes_.get_data().decode("utf-8").strip(), expected_data)

        # Check the metadata has been updated with the new name
        self.assertEqual(self._get_name_from_metadata(), expected_id)


class TestUpdateDeployFile(BaseTestCase):
    OLD_ID = "com.example.Hello"

    def setUp(self):
        super().setUp()

        self.deploy_file = tempfile.NamedTemporaryFile()

    def tearDown(self):
        self.deploy_file.close()

    def _populate_deploy_file(self, previous_ids):
        metadata = {}
        if previous_ids is not None:
            metadata['previous-ids'] = GLib.Variant('as', previous_ids)

        subpaths = []
        installed_size = 42
        data = ('origin', 'commit', subpaths, installed_size, metadata)
        variant = GLib.Variant('(ssasta{sv})', data)
        GLib.file_set_contents(self.deploy_file.name,
                               variant.get_data_as_bytes().get_data())

    def test_previous_ids_not_present(self):
        self._test(None,
                   ["com.example.Hello"])

    def test_previous_ids_empty(self):
        self._test([],
                   ["com.example.Hello"])

    def test_previous_ids_disjoint(self):
        self._test(["net.example.Howdy"],
                   [self.OLD_ID, "net.example.Howdy"])

    def test_previous_ids_contains_new(self):
        self._test(["com.example.Hello", "net.example.Howdy"],
                   [self.OLD_ID, "net.example.Howdy"])

    def test_add_multiple(self):
        self._test([],
                   [self.OLD_ID, "net.example.Howdy"],
                   frozenset((self.OLD_ID, "net.example.Howdy")))

    def _test(self, orig, expected, new_ids=frozenset((OLD_ID,))):
        self._populate_deploy_file(orig)
        eufr.update_deploy_file_with_previous_ids(
            self.deploy_file.name, new_ids,
        )
        modified = eufr.load_deploy_file(self.deploy_file.name)
        self.assertEqual(sorted(modified[4]['previous-ids']),
                         sorted(expected))
