# Copyright 2024 Endless OS Foundation LLC
# SPDX-License-Identifier: GPL-2.0-or-later

# pytest fixtures

import pytest


@pytest.fixture(autouse=True)
def default_env_vars(monkeypatch):
    monkeypatch.setenv('LANG', 'C.UTF-8')
