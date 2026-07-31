"""Shared pytest fixtures for laser-init test suite.

This module provides common fixtures used across multiple test files,
including ephemeral environment setup for integration testing.
"""

import importlib
import os
import shutil
from pathlib import Path

import pytest
import yaml

import laser.init.config as cfg


@pytest.fixture
def cli_env(tmp_path):
    """Create ephemeral environment for CLI execution.

    Sets up a temporary directory as current working directory with
    laser_config.yaml specifying cache and log directories within it.
    Reloads config module to pick up new configuration.

    Yields:
        dict: Environment info with 'work_dir', 'cache_dir', 'log_dir', 'original_dir'

    Teardown restores original directory, reloads config, and cleans up.
    """
    # Save original directory
    original_dir = Path.cwd()

    # Create cache and log directories
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # Write laser_config.yaml
    config_dict = {
        "cache_dir": str(cache_dir),
        "log_dir": str(log_dir),
    }
    config_file = tmp_path / "laser_config.yaml"
    config_file.write_text(yaml.dump(config_dict))

    # Change to temporary directory
    os.chdir(tmp_path)

    # Reload config module to pick up new laser_config.yaml in current directory
    importlib.reload(cfg)

    # Yield environment info
    env = {
        "work_dir": tmp_path,
        "cache_dir": cache_dir,
        "log_dir": log_dir,
        "original_dir": original_dir,
        "config_file": config_file,
    }

    yield env

    # Teardown: restore original directory
    os.chdir(original_dir)

    # Reload config module again to restore original configuration
    importlib.reload(cfg)

    # Clean up temporary directory
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
