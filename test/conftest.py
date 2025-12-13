"""Pytest configuration and shared fixtures."""
import os
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_env():
    """Fixture to mock environment variables."""
    with patch.dict(os.environ, {}, clear=False):
        yield os.environ


@pytest.fixture
def mock_subprocess():
    """Fixture to mock subprocess calls."""
    with patch('subprocess.run') as mock_run:
        yield mock_run


@pytest.fixture
def mock_popen():
    """Fixture to mock subprocess.Popen."""
    with patch('subprocess.Popen') as mock_popen_class:
        mock_process = MagicMock()
        mock_process.communicate.return_value = ('output', 'error')
        mock_process.returncode = 0
        mock_popen_class.return_value.__enter__.return_value = mock_process
        yield mock_popen_class


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Fixture to create a temporary home directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path
