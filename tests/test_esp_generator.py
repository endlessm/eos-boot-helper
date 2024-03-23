# Copyright © 2023 Endless OS Foundation, LLC
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
Tests for eos-esp-generator
"""

from contextlib import contextmanager
import json
import logging
import os
from pathlib import Path
import pytest
import sys
from textwrap import dedent

from .util import import_script_as_module

espgen = import_script_as_module('espgen', 'eos-esp-generator')

logger = logging.getLogger(__name__)
TESTSDIR = Path(os.path.dirname(__file__))
TESTSDATADIR = TESTSDIR / 'data'


@pytest.fixture(autouse=True)
def generator_environment(monkeypatch):
    """Generator environment fixture"""
    monkeypatch.setenv('SYSTEMD_IN_INITRD', '0')


@pytest.fixture
def root_dir(tmp_path):
    """Temporary root directory"""
    path = tmp_path / 'root'
    path.mkdir()
    path.joinpath('boot').mkdir()
    path.joinpath('efi').mkdir()
    return path


@pytest.fixture
def unit_dir(root_dir):
    """Temporary systemd generator unit directory"""
    path = root_dir / 'run/systemd/generator'
    path.mkdir(parents=True)
    return path


@pytest.fixture
def mock_system_data(monkeypatch):
    """System data mocking factory fixture

    Provides a function that can be called with the desired mocked data.
    This will override the generator calls that use findmnt and sfdisk.
    """
    def _mock_system_data(mounts, fstab, disks):
        with mounts.open() as f:
            mounts_data = json.load(f)['filesystems']
        logger.debug(f'mounts: {mounts_data}')

        def _fake_mount_data(root=Path('/')):
            return mounts_data

        monkeypatch.setattr(espgen, 'get_mount_data', _fake_mount_data)

        with fstab.open() as f:
            fstab_data = json.load(f)['filesystems']
        logger.debug(f'fstab: {fstab_data}')

        def _fake_fstab_data():
            return fstab_data

        monkeypatch.setattr(espgen, 'get_fstab_data', _fake_fstab_data)

        partitions = []
        for disk in disks:
            with disk.open() as f:
                disk_data = json.load(f)
            partitions += espgen._disk_to_partitions(disk_data)
        logger.debug(f'partitions: {partitions}')

        def _fake_partition_data():
            return partitions

        monkeypatch.setattr(espgen, 'get_partition_data', _fake_partition_data)

    return _mock_system_data


@contextmanager
def loader_device_part_uuid(value, root):
    """LoaderDevicePartUUID EFI variable context manager"""
    varpath = root / 'sys/firmware/efi/efivars' / espgen.LOADER_DEVICE_PART_UUID_EFIVAR
    varpath.parent.mkdir(parents=True, exist_ok=True)

    # Using the utf-16 codec for writing will add the byte order mark
    # (BOM). Select the native endian version.
    utf_16 = 'utf-16-le' if sys.byteorder == 'little' else 'utf-16-be'

    with open(varpath, 'wb') as f:
        f.write(b'\0\0\0\0')
        f.write(value.encode(utf_16))

        # Add 3 nul byte terminators like systemd-boot does.
        f.write(b'\0\0\0')

    try:
        yield
    finally:
        varpath.unlink()


# Dictionary of mocked data to use with the test_get_esp_mount() test.
ESP_MOUNT_TEST_DATA = {
    # Standard EOS with GPT partitioning.
    'gpt': {
        'mounts-init': TESTSDATADIR / 'espgen-gpt-amd64-mounts-init.json',
        'mounts-reload': TESTSDATADIR / 'espgen-gpt-amd64-mounts-reload.json',
        'fstab': TESTSDATADIR / 'espgen-gpt-amd64-fstab.json',
        'disks': [
            TESTSDATADIR / 'espgen-gpt-amd64-disk-root.json',
        ],
        'esp-mount': espgen.EspMount(
            source='/dev/vda1',
            target='/efi',
            type='vfat',
            umask='0077',
        ),
    },

    # Standard EOS with MBR partitioning.
    'mbr': {
        'mounts-init': TESTSDATADIR / 'espgen-mbr-amd64-mounts-init.json',
        'mounts-reload': TESTSDATADIR / 'espgen-mbr-amd64-mounts-reload.json',
        'fstab': TESTSDATADIR / 'espgen-mbr-amd64-fstab.json',
        'disks': [
            TESTSDATADIR / 'espgen-mbr-amd64-disk-root.json',
        ],
        'esp-mount': espgen.EspMount(
            source='/dev/vda1',
            target='/efi',
            type='vfat',
            umask='0077',
        ),
    },

    # Standard EOS with GPT partitioning and /efi in fstab.
    'efi-fstab': {
        'mounts-init': TESTSDATADIR / 'espgen-gpt-amd64-mounts-init.json',
        'mounts-reload': TESTSDATADIR / 'espgen-efi-fstab-amd64-mounts-reload.json',
        'fstab': TESTSDATADIR / 'espgen-efi-fstab-amd64-fstab.json',
        'disks': [
            TESTSDATADIR / 'espgen-gpt-amd64-disk-root.json',
        ],
        'esp-mount': None,
    },

    # PAYG with GPT partitioning.
    'payg': {
        'mounts-init': TESTSDATADIR / 'espgen-payg-amd64-mounts-init.json',
        'mounts-reload': TESTSDATADIR / 'espgen-payg-amd64-mounts-reload.json',
        'fstab': TESTSDATADIR / 'espgen-payg-amd64-fstab.json',
        'disks': [
            TESTSDATADIR / 'espgen-payg-amd64-disk-root.json',
        ],
        'esp-mount': espgen.EspMount(
            source='/dev/vda1',
            target='/boot',
            type='vfat',
            umask='0022',
        ),
    },

    # PAYG with GPT partitioning and XBOOTLDR partition. This is not
    # something we currently do, but we could to allow /boot to be on a
    # normal filesystem like ext4.
    'payg-xbootldr': {
        'mounts-init': TESTSDATADIR / 'espgen-payg-xbootldr-amd64-mounts-init.json',
        'mounts-reload': TESTSDATADIR / 'espgen-payg-xbootldr-amd64-mounts-reload.json',
        'fstab': TESTSDATADIR / 'espgen-payg-xbootldr-amd64-fstab.json',
        'disks': [
            TESTSDATADIR / 'espgen-payg-xbootldr-amd64-disk-root.json',
        ],
        'esp-mount': espgen.EspMount(
            source='/dev/vda1',
            target='/efi',
            type='vfat',
            umask='0077',
        ),
    },
}


@pytest.mark.parametrize('system', sorted(ESP_MOUNT_TEST_DATA.keys()))
def test_get_esp_mount(system, root_dir, mock_system_data, monkeypatch):
    """EspGenerator.get_esp_mount tests"""
    system_data = ESP_MOUNT_TEST_DATA[system]
    mounts_init = system_data['mounts-init']
    mounts_reload = system_data['mounts-reload']
    fstab = system_data['fstab']
    disks = system_data['disks']
    expected_mount = system_data['esp-mount']

    # Running during init.
    mock_system_data(mounts=mounts_init, fstab=fstab, disks=disks)
    generator = espgen.EspGenerator(root_dir)
    esp_mount = generator.get_esp_mount()
    assert esp_mount == expected_mount

    # If the generator is run in the initrd, it should do nothing.
    with monkeypatch.context() as mctx:
        mctx.setenv('SYSTEMD_IN_INITRD', '1')
        generator = espgen.EspGenerator(root_dir)
        esp_mount = generator.get_esp_mount()
        assert esp_mount is None

    # If the expected mount directory is /efi but there's no /efi
    # directory, nothing should be mounted since there's already a mount
    # on /boot.
    root_dir.joinpath('efi').rmdir()
    generator = espgen.EspGenerator(root_dir)
    esp_mount = generator.get_esp_mount()
    if expected_mount is None or expected_mount.target == '/efi':
        assert esp_mount is None
    else:
        assert esp_mount == expected_mount
    root_dir.joinpath('efi').mkdir()

    expected_esp_part = {}
    if expected_mount:
        partitions = espgen.get_partition_data()
        expected_esp_part = next(
            filter(lambda p: p['node'] == expected_mount.source, partitions),
        )

    # If the ESP disk is GPT partitioned, test the LoaderDevicePartUUID
    # EFI variable handling.
    if expected_esp_part.get('disk_label') == 'gpt':
        # Set it to the expected value.
        with loader_device_part_uuid(expected_esp_part['uuid'].upper(), root_dir):
            generator = espgen.EspGenerator(root_dir)
            esp_mount = generator.get_esp_mount()
            assert esp_mount == expected_mount

        # Set it to a different value. This should cause the mount to be
        # skipped.
        with loader_device_part_uuid('4859CD39-28DC-4C60-B509-C2A63A80483B', root_dir):
            generator = espgen.EspGenerator(root_dir)
            esp_mount = generator.get_esp_mount()
            assert esp_mount is None

    # Load the post-init mounts data to check that running during a
    # reload still creates the mount unit.
    mock_system_data(mounts=mounts_reload, fstab=fstab, disks=disks)
    generator = espgen.EspGenerator(root_dir)
    esp_mount = generator.get_esp_mount()
    assert esp_mount == expected_mount


def test_write_units(unit_dir):
    """EspMount.write_units tests"""
    esp_mount = espgen.EspMount(
        source='/dev/vda1',
        target='/efi',
        type='vfat',
        umask='0077',
    )
    esp_mount.write_units(unit_dir)
    automount_unit = unit_dir / 'efi.automount'
    mount_unit = unit_dir / 'efi.mount'
    local_fs_wants = unit_dir / 'local-fs.target.wants/efi.automount'
    units = set()
    for dirpath, dirnames, filenames in os.walk(unit_dir):
        units.update([unit_dir / dirpath / f for f in filenames])
    assert units == {automount_unit, mount_unit, local_fs_wants}
    assert not os.path.isabs(os.readlink(local_fs_wants))
    assert local_fs_wants.resolve() == automount_unit

    automount_contents = automount_unit.read_text()
    assert automount_contents == dedent("""\
    # Automatically generated by eos-esp-generator

    [Unit]
    Description=EFI System Partition Automount

    [Automount]
    Where=/efi
    TimeoutIdleSec=2min
    """)

    mount_contents = mount_unit.read_text()
    assert mount_contents == dedent("""\
    # Automatically generated by eos-esp-generator

    [Unit]
    Description=EFI System Partition Automount
    Requires=systemd-fsck@dev-vda1.service
    After=systemd-fsck@dev-vda1.service
    After=blockdev@dev-vda1.target

    [Mount]
    What=/dev/vda1
    Where=/efi
    Type=vfat
    Options=umask=0077,noauto,rw
    """)


def test_read_efivar(root_dir, caplog):
    """read_efivar tests"""
    var = 'Foo-7553c1d3-754b-47f3-a613-b9e2b860e8c1'
    varpath = root_dir / 'sys/firmware/efi/efivars' / var
    varpath.parent.mkdir(parents=True)

    # The first 32 bits are an attribute mask. Use all 1s so we can
    # better detect it leaking into the value.
    attr = b'\xff\xff\xff\xff'

    # Missing variable should return None.
    varpath.unlink(missing_ok=True)
    value = espgen.read_efivar(var, root_dir)
    assert value is None

    # Empty value.
    with open(varpath, 'wb') as f:
        f.write(attr)
    value = espgen.read_efivar(var, root_dir)
    assert value == b''

    # Actual contents.
    with open(varpath, 'wb') as f:
        f.write(attr)
        f.write(b'hello')
    value = espgen.read_efivar(var, root_dir)
    assert value == b'hello'

    # Invalid contents should log a warning and return None.
    with open(varpath, 'wb') as f:
        pass
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        value = espgen.read_efivar(var, root_dir)
    assert value is None
    assert caplog.record_tuples == [(
        espgen.logger.name,
        logging.WARNING,
        f'Invalid EFI variable {var} is less than 4 bytes',
    )]


def test_efivar_utf16_string(root_dir):
    """read_efivar_utf16_string tests"""
    var = 'Bar-7553c1d3-754b-47f3-a613-b9e2b860e8c1'
    varpath = root_dir / 'sys/firmware/efi/efivars' / var
    varpath.parent.mkdir(parents=True)

    # The first 32 bits are an attribute mask. Use all 1s so we can
    # better detect it leaking into the value.
    attr = b'\xff\xff\xff\xff'

    # Using the utf-16 codec for writing will add the byte order mark
    # (BOM). Select the native endian version.
    utf_16 = 'utf-16-le' if sys.byteorder == 'little' else 'utf-16-be'

    # Missing variable should return None.
    varpath.unlink(missing_ok=True)
    value = espgen.read_efivar_utf16_string(var, root_dir)
    assert value is None

    # Empty value.
    with open(varpath, 'wb') as f:
        f.write(attr)
    value = espgen.read_efivar_utf16_string(var, root_dir)
    assert value == ''

    # Actual contents.
    with open(varpath, 'wb') as f:
        f.write(attr)
        f.write('hello'.encode(utf_16))
    value = espgen.read_efivar_utf16_string(var, root_dir)
    assert value == 'hello'

    # Only nul terminator.
    with open(varpath, 'wb') as f:
        f.write(attr)
        f.write(b'\0\0')
    value = espgen.read_efivar_utf16_string(var, root_dir)
    assert value == ''

    # Various nul byte terminators.
    for n in range(6):
        term = b'\0' * n
        with open(varpath, 'wb') as f:
            f.write(attr)
            f.write('hello'.encode(utf_16))
            f.write(term)
        value = espgen.read_efivar_utf16_string(var, root_dir)
        assert value == 'hello'

    # Unicode.
    uface = '\N{UPSIDE-DOWN FACE}'  # 🙃
    for term in (b'', b'\0\0'):
        with open(varpath, 'wb') as f:
            f.write(attr)
            f.write(uface.encode(utf_16))
            f.write(term)
        value = espgen.read_efivar_utf16_string(var, root_dir)
        assert value == uface
