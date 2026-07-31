"""Configuration loading and management for laser-init.

This module handles loading user configuration from YAML or JSON files located in
the current working directory or the user's home directory. Configuration values
can be used to set default data sources, API keys, and other preferences.

Configuration File Locations (in order of precedence):

  1. ./laser_config.yaml (current directory)
  2. ./laser_config.json (current directory)
  3. ~/.laser/laser_config.yaml (user home directory)
  4. ~/.laser/laser_config.json (user home directory)

The first file found is loaded and subsequent files are ignored.

Configuration File Format:
    YAML example:
        ```yaml
        shape_source: unocha
        raster_source: worldpop
        stats_source: unwpp
        openai_api_key: sk-your-key-here
        anthropic_api_key: sk-ant-your-key-here
        cache_dir: /path/to/cache
        log_dir: /path/to/logs
        ```

    JSON example:
        ```json
        {
          "shape_source": "unocha",
          "raster_source": "worldpop",
          "stats_source": "unwpp",
          "openai_api_key": "sk-your-key-here",
          "anthropic_api_key": "sk-ant-your-key-here",
          "cache_dir": "/path/to/cache",
          "log_dir": "/path/to/logs"
        }
        ```

Supported Configuration Keys:

  - `shape_source` (str): Default shapefile data source (unocha, geoboundaries, gadm)
  - `raster_source` (str): Default population raster source (worldpop)
  - `stats_source` (str): Default demographic statistics source (unwpp)
  - `openai_api_key` (str): OpenAI API key for enhanced country name matching
  - `anthropic_api_key` (str): Anthropic API key for enhanced country name matching
  - `cache_dir` (str): Directory for caching downloaded data
  - `log_dir` (str): Directory for writing log files

Module Attributes:

  - `VERSION` (str): The version string of the laser-init package.
  - `configuration` (dict): Dictionary containing the loaded configuration values.
        Empty dict if no configuration file is found or if parsing fails.

Usage:
    ```python
    from laser.init.config import configuration, VERSION

    # Access configuration values
    shape_source = configuration.get("shape_source", "unocha")
    api_key = configuration.get("openai_api_key")

    # Check version
    print(f"laser-init version: {VERSION}")
    ```

Notes:
    - Configuration is loaded automatically when the module is imported
    - If a configuration file has YAML or JSON syntax errors, a warning is issued
      and an empty configuration is used instead. The warning message will include
      the file path and specific parsing error details.
    - Command-line arguments override configuration file values
    - Environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY) are checked if not
      present in the configuration file

Warnings:
    yaml.YAMLError: Issued when a .yaml configuration file has syntax errors
    json.JSONDecodeError: Issued when a .json configuration file has syntax errors

Examples:
    Create a configuration file to set default preferences:

    ```shell
    # Create user configuration directory
    mkdir -p ~/.laser

    # Create configuration file
    cat > ~/.laser/laser_config.yaml << EOF
    shape_source: unocha
    raster_source: worldpop
    stats_source: unwpp
    EOF
    ```

    Then use laser-init with these defaults applied automatically.
"""

import json
import warnings
from pathlib import Path

import yaml

from laser.init import __version__

__all__ = ["VERSION", "configuration", "default_cache_directory", "default_log_directory"]

VERSION = __version__

default_cache_directory = Path.home() / ".laser" / "cache"
default_log_directory = Path.home() / ".laser" / "logs"

configuration = {}

candidates = [
    Path.cwd() / "laser_config.yaml",
    Path.cwd() / "laser_config.json",
    Path.home() / ".laser" / "laser_config.yaml",
    Path.home() / ".laser" / "laser_config.json",
]

# set some defaults:
if any(path.is_file() for path in candidates):
    # look for laser_config.[yaml,json]
    # prefer the current working directory
    # then look in the user's home directory / .laser
    for path in candidates:
        if path.is_file():
            if path.suffix.lower() == ".yaml":
                try:
                    configuration = yaml.safe_load(path.read_text())
                except yaml.YAMLError as e:
                    warnings.warn(
                        f"Error parsing YAML configuration file {path}: {e}", stacklevel=2
                    )
                    configuration = {}
                break
            elif path.suffix.lower() == ".json":
                try:
                    configuration = json.loads(path.read_text())
                except json.JSONDecodeError as e:
                    warnings.warn(
                        f"Error parsing JSON configuration file {path}: {e}", stacklevel=2
                    )
                    configuration = {}
                break
else:
    warnings.warn("Did not find a laser configuration file. Using default.", stacklevel=2)
    configuration = {
        "cache_dir": str(default_cache_directory),
        "log_dir": str(default_log_directory),
        "shape_source": "unocha",
        "raster_source": "worldpop",
        "stats_source": "unwpp",
        # "openai_api_key": "sk-your-key-here",
        # "anthropic_api_key": "sk-ant-your-key-here",
    }
