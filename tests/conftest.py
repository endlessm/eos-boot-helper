# Copyright 2024 Endless OS Foundation LLC
# SPDX-License-Identifier: GPL-2.0-or-later

# pytest fixtures

import pytest
from shutil import copyfile, copytree

from .util import EFIVARFS_PATH


@pytest.fixture(autouse=True)
def default_env_vars(monkeypatch):
    monkeypatch.setenv('LANG', 'C.UTF-8')


@pytest.fixture
def efivarfs(tmp_path, monkeypatch):
    """Temporary efivarfs data

    Copy the test efivarfs data to a temporary location. The environment
    variable EFIVARFS_PATH is set to the temporary location. This is supported
    by libefivar.
    """
    # Only the data is copied in case EFIVARFS_PATH is read only like
    # during distcheck. None of the metadata matters here.
    tmp_efivarfs = tmp_path / 'efivars'
    copytree(EFIVARFS_PATH, tmp_efivarfs, copy_function=copyfile)

    # libefivar expects this to end with a trailing /.
    monkeypatch.setenv('EFIVARFS_PATH', f'{tmp_efivarfs}/')

    return tmp_efivarfs
