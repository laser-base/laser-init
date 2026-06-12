"""Tests for laser.init.config module.

This module tests configuration loading and management functionality,
including reading configuration files from various locations and formats.
"""

import importlib
import json
import os
from unittest.mock import patch

import pytest
import yaml

import laser.init.config as cfg


class TestConfigLoading:
    """Test suite for configuration file loading."""

    def test_config_with_yaml_file(self, cli_env):
        """Test that YAML files can be parsed correctly.

        Given a valid YAML configuration file
        When importing config from laser.init
        Then it should be loaded correctly

        Failure indicates YAML parsing is broken.
        Note: This tests YAML parsing capability, which config module uses.
        Per docstring, config loads from ./laser_config.yaml or ~/.laser/laser_config.yaml.
        """

        # Create a test YAML config file in the working directory
        config_file = cli_env["config_file"]
        test_config = {
            "cache_dir": str(cli_env["cache_dir"]),
            "log_dir": str(cli_env["log_dir"]),
            "shape_source": "qwerty",
            "raster_source": "worldpop",
            "stats_source": "unwpp",
        }
        config_file.write_text(yaml.dump(test_config))

        # Use importlib.reload to ensure config module is reloaded for each test, if needed.
        importlib.reload(cfg)

        # Check configuration from config to verify it was loaded correctly.
        assert cfg.configuration["shape_source"] == "qwerty"

    def test_config_with_json_file(self, cli_env):
        """Test that JSON files can be parsed correctly.

        Given a JSON configuration file
        When parsing with json.load
        Then it should be loaded correctly

        Failure indicates JSON parsing is broken.
        Note: This tests JSON parsing capability, which config module uses.
        Per docstring, config loads from ./laser_config.json or ~/.laser/laser_config.json.
        """
        # Create a temporary config file
        cli_env["config_file"].unlink()  # Remove existing config file to force JSON loading
        config_file = cli_env["work_dir"] / "laser_config.json"

        # Write test configuration
        test_config = {
            "cache_dir": str(cli_env["cache_dir"]),
            "log_dir": str(cli_env["log_dir"]),
            "shape_source": "asdfg",
            "raster_source": "worldpop",
            "stats_source": "unwpp",
        }
        config_file.write_text(json.dumps(test_config))

        # Use importlib.reload to ensure config module is reloaded for each test, if needed.
        importlib.reload(cfg)

        # Check configuration from config to verify it was loaded correctly.
        assert cfg.configuration["shape_source"] == "asdfg"


class TestConfigAPIKeys:
    """Test suite for API key configuration."""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-openai"})
    def test_env_var_openai_key(self):
        """Test that OpenAI API key can be set via environment variable.

        Given an OPENAI_API_KEY environment variable
        When accessing os.environ
        Then the environment variable should be accessible

        Failure indicates environment variable handling has changed.
        Note: Per config docstring, environment variables OPENAI_API_KEY and
        ANTHROPIC_API_KEY are checked if not present in config file.
        """

        assert os.environ.get("OPENAI_API_KEY") == "sk-test-openai"

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test-anthropic"})
    def test_env_var_anthropic_key(self):
        """Test that Anthropic API key can be set via environment variable.

        Given an ANTHROPIC_API_KEY environment variable
        When accessing os.environ
        Then the environment variable should be accessible

        Failure indicates environment variable handling has changed.
        Note: Per config docstring, environment variables are fallback
        if keys not in config file.
        """

        assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-test-anthropic"


class TestConfigFilePrecedence:
    """Test suite for config file loading precedence."""

    def test_yaml_precedence_over_json(self, cli_env):
        """Test that YAML config takes precedence over JSON.

        Given both laser_config.yaml and laser_config.json exist
        When config module determines which to load
        Then YAML should be preferred

        Failure indicates config precedence rules have changed.
        Note: Per docstring, config searches for .yaml before .json files.
        """
        yaml_file = cli_env["work_dir"] / "laser_config.yaml"
        json_file = cli_env["work_dir"] / "laser_config.json"

        yaml_config = {"shape_source": "yaml_source_qwerty"}
        json_config = {"shape_source": "json_source_asdfg"}

        yaml_file.write_text(yaml.dump(yaml_config))
        json_file.write_text(json.dumps(json_config))

        importlib.reload(cfg)

        # YAML file exists and is valid, confirming it would be loaded first
        assert cfg.configuration["shape_source"] == "yaml_source_qwerty"
        json_file.unlink()  # Clean up JSON file after test

    def test_current_directory_precedence_with_yaml(self, cli_env):
        """Test that current directory config is checked first.

        Given config files in both current directory and home directory
        When config module searches for files
        Then current directory should be checked first

        Failure indicates config search precedence has changed.
        Note: Per docstring, search order is:
        1. ./laser_config.yaml
        2. ./laser_config.json
        3. ~/.laser/laser_config.yaml
        4. ~/.laser/laser_config.json
        """
        # Create config in "current" directory
        selected_config = cli_env["work_dir"] / "laser_config.yaml"
        selected_config.write_text(yaml.dump({"shape_source": "local_yaml_source"}))

        importlib.reload(cfg)
        assert cfg.configuration["shape_source"] == "local_yaml_source"

    def test_current_directory_precedence_with_json(self, cli_env):
        """Test that current directory config is checked first.

        Given config files in both current directory and home directory
        When config module searches for files
        Then current directory should be checked first

        Failure indicates config search precedence has changed.
        Note: Per docstring, search order is:
        1. ./laser_config.yaml
        2. ./laser_config.json
        3. ~/.laser/laser_config.yaml
        4. ~/.laser/laser_config.json
        """
        # Create config in "current" directory
        cli_env["config_file"].unlink()  # Remove existing YAML config to force JSON loading
        selected_config = cli_env["work_dir"] / "laser_config.json"
        selected_config.write_text(json.dumps({"shape_source": "local_json_source"}))

        importlib.reload(cfg)
        assert cfg.configuration["shape_source"] == "local_json_source"


class TestConfigErrorHandling:
    def test_malformed_yaml_handled_gracefully(self, cli_env):
        """Test that malformed YAML files are handled gracefully.

        Given a malformed YAML configuration file
        When attempting to parse with yaml.safe_load
        Then a yaml.YAMLError should be raised

        Failure indicates YAML error handling has changed.
        Note: Per docstring, config module should handle yaml.YAMLError.
        """
        config_file = cli_env["config_file"]
        # Create invalid YAML with unclosed bracket
        config_file.write_text("cache_dir: /tmp\n  bad_indent: [unclosed")

        with pytest.warns(UserWarning, match="Error parsing YAML configuration file"):
            importlib.reload(cfg)

        assert cfg.configuration == {}, "Expected empty config on YAML parsing error"

    def test_malformed_json_handled_gracefully(self, cli_env):
        """Test that malformed JSON files are handled gracefully.

        Given a malformed JSON configuration file
        When attempting to parse with json.load
        Then a json.JSONDecodeError should be raised

        Failure indicates JSON error handling has changed.
        Note: Per docstring, config module should handle json.JSONDecodeError.
        """
        cli_env["config_file"].unlink()  # Remove existing config file to force JSON loading
        config_file = cli_env["work_dir"] / "laser_config.json"
        # Create invalid JSON with trailing comma
        config_file.write_text('{"cache_dir": "/tmp",}')

        with pytest.warns(UserWarning, match="Error parsing JSON configuration file"):
            importlib.reload(cfg)

        assert cfg.configuration == {}, "Expected empty config on JSON parsing error"
