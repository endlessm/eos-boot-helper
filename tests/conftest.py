# pytest fixtures
# https://docs.pytest.org/en/stable/how-to/fixtures.html

import pytest


@pytest.fixture(autouse=True)
def default_env_vars(monkeypatch):
    monkeypatch.setenv('LANG', 'C.UTF-8')
