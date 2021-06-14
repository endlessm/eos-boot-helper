#!/usr/bin/python3

# test_split_flatpak_repo.py: Tests for eos-split-flatpak-repo
#
# Copyright © 2021 Endless OS Foundation LLC
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

"""
Tests eos-split-flatpak-repo
"""

import filecmp
import gi
import logging
import os
import random
import shutil
import tempfile

from .util import (
    BaseTestCase, system_script, import_script_as_module, relative_link
)

gi.require_version("OSTree", "1.0")
from gi.repository import GLib, Gio, OSTree  # noqa: E402


logger = logging.getLogger(__name__)
esfr = import_script_as_module("esfr", system_script("eos-split-flatpak-repo"))


class TestSplitRepo(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

        self.tmp = tempfile.mkdtemp()

        # Create a root filesystem at tmpdir/root and initialize the
        # sysroot at /sysroot with an eos OS deployment.
        self.root = os.path.join(self.tmp, 'root')
        self.sysroot_path = os.path.join(self.root, 'sysroot')
        os.makedirs(self.sysroot_path)
        self.sysroot = OSTree.Sysroot.new(
            Gio.File.new_for_path(self.sysroot_path))
        self.sysroot.ensure_initialized()
        self.sysroot.init_osname('eos')

        # Get the sysroot's ostree repo and resolve the realpath since
        # the returned path is likely in /proc/self/fd. This should
        # result in /sysroot/ostree/repo.
        _, self.os_repo = self.sysroot.get_repo()
        self.os_repo_path = os.path.realpath(
            self.os_repo.get_path().get_path())

        # Set the repo locking timeout to 0 seconds so that locking
        # failures don't block tests.
        config = self.os_repo.copy_config()
        config.set_integer('core', 'lock-timeout-secs', 0)
        self.os_repo.write_config(config)
        self.os_repo.reload_config()

        # /sysroot/ostree
        self.ostree_path = os.path.dirname(self.os_repo_path)
        # /ostree
        self.root_ostree_path = os.path.join(self.root, 'ostree')
        # /ostree/repo
        self.root_os_repo_path = os.path.join(self.root_ostree_path, 'repo')
        # /sysroot/ostree/deploy
        self.deploy_path = os.path.join(self.ostree_path, 'deploy')
        # /sysroot/ostree/deploy/eos/var
        # This is what gets mounted to /var on a running system.
        self.var_path = os.path.join(self.deploy_path, 'eos/var')
        # /sysroot/ostree/deploy/eos/var/lib/flatpak
        self.flatpak_dir_path = os.path.join(self.var_path, 'lib/flatpak')
        # /sysroot/ostree/deploy/eos/var/lib/flatpak/repo
        self.flatpak_repo_path = os.path.join(self.flatpak_dir_path, 'repo')
        # /sysroot/flatpak
        self.sys_flatpak_dir_path = os.path.join(self.sysroot_path, 'flatpak')
        # /sysroot/flatpak/repo
        self.sys_flatpak_repo_path = os.path.join(self.sys_flatpak_dir_path,
                                                  'repo')

        # Emulate a booted system with:
        #
        # /ostree -> /sysroot/ostree
        # /sysroot/flatpak/repo -> /ostree/repo
        # /sysroot/ostree/deploy/eos/var/lib/flatpak -> /sysroot/flatpak
        #
        # In a real system these are absolute links, but we use relative
        # here so that the resolved paths stay within the test root.
        relative_link(self.ostree_path, self.root_ostree_path)
        os.makedirs(self.sys_flatpak_dir_path)
        relative_link(self.root_os_repo_path, self.sys_flatpak_repo_path)
        relative_link(self.sys_flatpak_dir_path, self.flatpak_dir_path)

        # Test that the symlinks resolve as expected.
        self.assertTrue(
            os.path.samefile(self.ostree_path, self.root_ostree_path)
        )
        self.assertTrue(
            os.path.samefile(self.os_repo_path, self.root_os_repo_path)
        )
        self.assertTrue(
            os.path.samefile(self.sys_flatpak_dir_path, self.flatpak_dir_path)
        )
        self.assertTrue(
            os.path.samefile(self.sys_flatpak_repo_path,
                             self.flatpak_repo_path)
        )
        self.assertTrue(
            os.path.samefile(self.os_repo_path, self.sys_flatpak_repo_path)
        )

        # Make sure remotes are added in the config file like on a real
        # system.
        config = self.os_repo.copy_config()
        config.set_boolean('core', 'add-remotes-config-dir', False)
        self.os_repo.write_config(config)
        self.os_repo.reload_config()

        # Add remotes
        self.os_repo.remote_add(
            'eos',
            'https://ostree.endlessm.com/ostree/eos',
            GLib.Variant('a{sv}', {
                # Mark the eos remote as not used for flatpaks
                'xa.disable': GLib.Variant('b', True),
            })
        )
        self.os_repo.remote_add(
            'eos-sdk',
            'https://ostree.endlessm.com/ostree/eos-sdk'
        )
        self.os_repo.remote_add(
            'flathub',
            'https://dl.flathub.org/repo/'
        )
        self.os_repo.reload_config()

    def tearDown(self):
        if not os.getenv('EBH_SKIP_CLEANUP'):
            logger.info('Deleting tmp directory %s', self.tmp)
            shutil.rmtree(self.tmp)
        else:
            logger.info('Skipping cleanup of tmp directory %s', self.tmp)

    def random_commit(self, repo, refspecs, parent=None):
        """Create a commit with random contents

        All refspecs will be set to the commit. If parent is specified
        it will be used as the commit's parent.
        """
        with tempfile.TemporaryDirectory(dir=self.tmp) as files:
            for sub in ('a', 'b/c'):
                path = os.path.join(files, sub)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                content = random.getrandbits(16 * 8).to_bytes(16, 'little')
                with open(path, 'wb') as f:
                    f.write(content)

            repo.prepare_transaction()
            try:
                mtree = OSTree.MutableTree.new()
                repo.write_directory_to_mtree(Gio.File.new_for_path(files),
                                              mtree, None)
                _, root = repo.write_mtree(mtree)
                _, checksum = repo.write_commit(parent, 'Test commit', None,
                                                None, root)
                logger.debug('Created commit %s', checksum)
                for refspec in refspecs:
                    logger.debug('Setting refspec %s to %s', refspec, checksum)
                    repo.transaction_set_refspec(refspec, checksum)
                repo.commit_transaction()
            except:  # noqa: E722
                repo.abort_transaction()
                raise

        return dict.fromkeys(refspecs, checksum)

    def create_os_commits(self):
        """Create some OS commits and return the refs"""
        os_refs = {}

        os_refs.update(self.random_commit(
            self.os_repo,
            ('eos:os/eos/amd64/eos3a', 'ostree/0/1/0')
        ))
        os_refs.update(self.random_commit(
            self.os_repo,
            ('eos:os/eos/amd64/eos3a', 'ostree/0/1/1'),
            os_refs['eos:os/eos/amd64/eos3a']
        ))

        return os_refs

    def create_flatpak_commits(self):
        """Create some flatpak commits and return the refs"""
        flatpak_refs = {}

        flatpak_refs.update(self.random_commit(
            self.os_repo, ('flathub:ostree-metadata',)
        ))
        flatpak_refs.update(self.random_commit(
            self.os_repo, ('flathub:appstream2/x86_64',)
        ))
        flatpak_refs.update(self.random_commit(
            self.os_repo,
            ('flathub:app/org.gnome.Totem/x86_64/stable',
             'deploy/app/org.gnome.Totem/x86_64/stable')
        ))
        flatpak_refs.update(self.random_commit(
            self.os_repo,
            ('flathub:runtime/org.gnome.Totem.Locale/x86_64/stable',
             'deploy/runtime/org.gnome.Totem.Locale/x86_64/stable')
        ))
        flatpak_refs.update(self.random_commit(
            self.os_repo,
            ('flathub:runtime/org.freedesktop.Platform/x86_64/20.08',
             'deploy/runtime/org.freedesktop.Platform/x86_64/20.08')
        ))

        flatpak_refs.update(self.random_commit(
            self.os_repo, ('eos-sdk:ostree-metadata',)
        ))
        flatpak_refs.update(self.random_commit(
            self.os_repo, ('eos-sdk:appstream2/x86_64',)
        ))
        flatpak_refs.update(self.random_commit(
            self.os_repo,
            ('eos-sdk:runtime/com.endlessm.apps.Platform/x86_64/6',
             'deploy/runtime/com.endlessm.apps.Platform/x86_64/6')
        ))

        return flatpak_refs

    def test_split(self):
        """Full test of repo splitting"""
        orig_os_refs = self.create_os_commits()
        orig_flatpak_refs = self.create_flatpak_commits()

        split = esfr.split_repo(root=self.root)
        self.assertTrue(split)

        self.assertFalse(
            os.path.samefile(self.os_repo_path, self.flatpak_repo_path)
        )
        self.assertFalse(os.path.exists(self.sys_flatpak_dir_path))

        os_repo = OSTree.Repo.new(Gio.File.new_for_path(self.os_repo_path))
        os_repo.open()
        _, os_refs = os_repo.list_refs()
        self.assertEqual(os_refs, orig_os_refs)
        os_remotes = set(os_repo.remote_list())
        self.assertEqual(os_remotes, {'eos'})

        flatpak_repo = OSTree.Repo.new(
            Gio.File.new_for_path(self.flatpak_repo_path))
        flatpak_repo.open()
        _, flatpak_refs = flatpak_repo.list_refs()
        self.assertEqual(flatpak_refs, orig_flatpak_refs)
        flatpak_remotes = set(flatpak_repo.remote_list())
        self.assertEqual(flatpak_remotes, {'flathub', 'eos-sdk'})

        # Check that the flatpak repo has been converted to bare-user-only
        flatpak_repo_config = flatpak_repo.get_config()
        repo_mode = flatpak_repo_config.get_string('core', 'mode')
        self.assertEqual(repo_mode, 'bare-user-only')

        # Running again should do nothing
        with self.assertLogs(esfr.logger, logging.INFO) as logs:
            split = esfr.split_repo(root=self.root)
        self.assertFalse(split)
        self.assertEqual(logs.output, [
            ('INFO:eos-split-flatpak-repo:OSTree repo and '
             'Flatpak repo have already been split'),
            ('INFO:eos-split-flatpak-repo:Flatpak dir '
             f'{self.flatpak_dir_path} is not a symlink'),
        ])

    def test_split_other(self):
        """Test that other refs stay in both repos"""
        refs = self.random_commit(self.os_repo, ('foo/bar/baz',))
        split = esfr.split_repo(root=self.root)
        self.assertTrue(split)

        os_repo = OSTree.Repo.new(Gio.File.new_for_path(self.os_repo_path))
        os_repo.open()
        _, os_refs = os_repo.list_refs()
        self.assertEqual(os_refs, refs)

        flatpak_repo = OSTree.Repo.new(
            Gio.File.new_for_path(self.flatpak_repo_path))
        flatpak_repo.open()
        _, flatpak_refs = flatpak_repo.list_refs()
        self.assertEqual(flatpak_refs, refs)

    def test_split_orphaned(self):
        """Test that orphaned refs go to the right places"""
        orig_os_refs = self.create_os_commits()
        orig_flatpak_refs = self.create_flatpak_commits()

        # Delete an OS and flatpak remote
        self.os_repo.remote_delete('eos')
        self.os_repo.remote_delete('eos-sdk')
        split = esfr.split_repo(root=self.root)
        self.assertTrue(split)

        # The OS repo should have the original OS refs + the deleted
        # flatpak repo's ostree-metadata ref.
        os_repo = OSTree.Repo.new(Gio.File.new_for_path(self.os_repo_path))
        os_repo.open()
        _, os_refs = os_repo.list_refs()
        expected_refs = orig_os_refs.copy()
        expected_refs['eos-sdk:ostree-metadata'] = \
            orig_flatpak_refs['eos-sdk:ostree-metadata']
        self.assertEqual(os_refs, expected_refs)

        # The flatpak repo should only have the original flatpak refs
        # since the OS remote didn't have an ostree-metadata ref.
        flatpak_repo = OSTree.Repo.new(
            Gio.File.new_for_path(self.flatpak_repo_path))
        flatpak_repo.open()
        _, flatpak_refs = flatpak_repo.list_refs()
        self.assertEqual(flatpak_refs, orig_flatpak_refs)

    def test_prune(self):
        """Test if repos are pruned when requested"""
        self.create_os_commits()
        self.create_flatpak_commits()
        esfr.split_repo(prune=True, root=self.root)

        os_repo = OSTree.Repo.new(Gio.File.new_for_path(self.os_repo_path))
        os_repo.open()
        pruned = os_repo.prune(OSTree.RepoPruneFlags.REFS_ONLY, -1)[2]
        self.assertEqual(pruned, 0)

        flatpak_repo = OSTree.Repo.new(
            Gio.File.new_for_path(self.flatpak_repo_path))
        flatpak_repo.open()
        pruned = flatpak_repo.prune(OSTree.RepoPruneFlags.REFS_ONLY, -1)[2]
        self.assertEqual(pruned, 0)

    def test_no_prune(self):
        """Test if repos are not pruned when not requested"""
        self.create_os_commits()
        self.create_flatpak_commits()
        esfr.split_repo(prune=False, root=self.root)

        os_repo = OSTree.Repo.new(Gio.File.new_for_path(self.os_repo_path))
        os_repo.open()
        pruned = os_repo.prune(OSTree.RepoPruneFlags.REFS_ONLY, -1)[2]
        self.assertGreater(pruned, 0)

        flatpak_repo = OSTree.Repo.new(
            Gio.File.new_for_path(self.flatpak_repo_path))
        flatpak_repo.open()
        pruned = flatpak_repo.prune(OSTree.RepoPruneFlags.REFS_ONLY, -1)[2]
        self.assertGreater(pruned, 0)

    def test_gather_refs(self):
        """Test gather_refs functionality"""
        self.create_os_commits()
        self.create_flatpak_commits()
        self.random_commit(
            self.os_repo,
            (
                'ostree-metadata',
                'appstream/x86_64',
                'appstream2/x86_64',
                'foobar',
                'deleted:ostree-metadata',
                'deleted:appstream2/x86_64',
                'deleted:app/com.example.Foo/x86_64/stable',
                'deploy/app/com.example.Foo/x86_64/stable',
            )
        )

        os_remotes = ['eos']
        flatpak_remotes = ['eos-sdk', 'flathub']
        with self.assertLogs(esfr.logger, logging.WARNING) as logs:
            os_refs, flatpak_refs, other_refs = esfr.gather_refs(
                self.os_repo, os_remotes, flatpak_remotes)
        self.assertEqual(logs.output, [
            ('WARNING:eos-split-flatpak-repo:'
             'Refspec deleted:app/com.example.Foo/x86_64/stable remote '
             'deleted no longer exists'),
            ('WARNING:eos-split-flatpak-repo:'
             'Refspec deleted:appstream2/x86_64 remote '
             'deleted no longer exists'),
            ('WARNING:eos-split-flatpak-repo:'
             'Refspec deleted:ostree-metadata remote '
             'deleted no longer exists'),
            ('WARNING:eos-split-flatpak-repo:'
             'Ignoring unrecognized ref: foobar'),
        ])
        self.assertEqual(os_refs, [
            'eos:os/eos/amd64/eos3a',
            'ostree/0/1/0',
            'ostree/0/1/1',
        ])
        self.assertEqual(flatpak_refs, [
            'deleted:app/com.example.Foo/x86_64/stable',
            'deleted:appstream2/x86_64',
            'deploy/app/com.example.Foo/x86_64/stable',
            'deploy/app/org.gnome.Totem/x86_64/stable',
            'deploy/runtime/com.endlessm.apps.Platform/x86_64/6',
            'deploy/runtime/org.freedesktop.Platform/x86_64/20.08',
            'deploy/runtime/org.gnome.Totem.Locale/x86_64/stable',
            'eos-sdk:appstream2/x86_64',
            'eos-sdk:ostree-metadata',
            'eos-sdk:runtime/com.endlessm.apps.Platform/x86_64/6',
            'flathub:app/org.gnome.Totem/x86_64/stable',
            'flathub:appstream2/x86_64',
            'flathub:ostree-metadata',
            'flathub:runtime/org.freedesktop.Platform/x86_64/20.08',
            'flathub:runtime/org.gnome.Totem.Locale/x86_64/stable',
        ])
        self.assertEqual(other_refs, [
            'appstream/x86_64',
            'appstream2/x86_64',
            'deleted:ostree-metadata',
            'foobar',
            'ostree-metadata',
        ])

        # Make sure an exception is raised if a remote is in both lists.
        os_remotes = ['eos']
        flatpak_remotes = ['eos', 'eos-sdk', 'flathub']
        with self.assertRaisesRegex(esfr.SplitError,
                                    'eos in both OS and Flatpak remotes'):
            esfr.gather_refs(self.os_repo, os_remotes, flatpak_remotes)

    def assertDircmpNoDiffs(self, dircmp):
        """Recursively assert that a dircmp object has no differences"""
        logger.debug("Comparing %s to %s", dircmp.left, dircmp.right)
        self.assertEqual(dircmp.left_only, [])
        self.assertEqual(dircmp.right_only, [])
        self.assertEqual(dircmp.diff_files, [])

        for sub in dircmp.subdirs.values():
            self.assertDircmpNoDiffs(sub)

    def test_duplicate_repo(self):
        """Test duplicate_repo functionality"""
        self.create_os_commits()
        self.create_flatpak_commits()

        dup_path = os.path.join(self.tmp, 'dup')
        esfr.duplicate_repo(self.os_repo_path, dup_path)

        # The directories should be identical.
        dcmp = filecmp.dircmp(self.os_repo_path, dup_path, ignore=[])
        self.assertDircmpNoDiffs(dcmp)

        # Make sure the number of hardlinks is correct.
        for root, dirs, files in os.walk(dup_path):
            repo_dir = os.path.relpath(root, dup_path).split(os.sep)[0]
            if repo_dir in ('objects', 'deltas'):
                expected_links = 2
            else:
                expected_links = 1
            for f in files:
                path = os.path.join(root, f)
                logger.debug('Getting number of links for %s', path)
                stat = os.lstat(path)
                self.assertEqual(stat.st_nlink, expected_links)
