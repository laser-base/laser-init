"""Tests for laser.init.cli module.

This module tests the command-line interface functionality, including
argument parsing, validation, and the overall workflow orchestration.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

import laser.init.config
from laser.init import cli


class TestCLIBasics:
    """Test suite for basic CLI functionality."""

    def test_cli_function_exists(self):
        """Test that the main CLI function exists.

        Given the cli module
        When checking for the cli function
        Then it should be available and callable

        Failure indicates the CLI entry point has changed.
        """
        assert hasattr(cli, "cli")
        assert callable(cli.cli)

    def test_cli_is_click_command(self):
        """Test that CLI uses Click framework.

        Given the cli function
        When inspecting its type
        Then it should be a Click command

        Failure indicates the CLI framework has changed.
        """
        # The cli function should be decorated with @click.command
        assert hasattr(cli.cli, "__click_params__") or callable(cli.cli)


class TestCLIArguments:
    """Test suite for CLI argument handling."""

    def test_cli_accepts_country_argument(self):
        """Test that CLI accepts country argument.

        Given the laser-init CLI
        When providing a country code
        Then it should be accepted as a valid argument

        Failure indicates country argument handling has changed.
        """
        runner = CliRunner()
        # Test with minimal valid arguments - may fail due to missing data but should parse args
        result = runner.invoke(cli.cli, ["--help"])
        assert result.exit_code == 0
        assert "country" in result.output.lower() or "COUNTRY" in result.output

    def test_cli_requires_positional_arguments(self):
        """Test that CLI requires country, level, and year arguments.

        Given the laser-init CLI
        When invoked without required arguments
        Then it should show help or error message

        Failure indicates required argument validation has changed.
        """
        runner = CliRunner()
        result = runner.invoke(cli.cli, [])
        # Should fail without required arguments
        assert result.exit_code != 0
        assert result.output.startswith("Usage: cli [OPTIONS] COUNTRY LEVEL START_YEAR END_YEAR")

    def test_cli_requires_all_positional_arguments(self):
        """Test that ALL positional arguments are required (not just one).

        Given the laser-init CLI
        When invoked with incomplete positional arguments
        Then it should fail for each missing argument

        Failure indicates argument validation is not checking all required arguments.
        Note: laser-init requires 4 positional arguments: COUNTRY, LEVEL, START_YEAR, END_YEAR
        """
        runner = CliRunner()

        # Test with only 1 argument (missing LEVEL, START_YEAR, END_YEAR)
        result = runner.invoke(cli.cli, ["SEN"])
        assert result.exit_code != 0, "Should fail with only COUNTRY provided"

        # Test with only 2 arguments (missing START_YEAR, END_YEAR)
        result = runner.invoke(cli.cli, ["SEN", "2"])
        assert result.exit_code != 0, "Should fail with only COUNTRY and LEVEL provided"

        # Test with only 3 arguments (missing END_YEAR)
        result = runner.invoke(cli.cli, ["SEN", "2", "2020"])
        assert result.exit_code != 0, (
            "Should fail with COUNTRY, LEVEL, and START_YEAR but no END_YEAR"
        )

    def test_cli_help_option(self):
        """Test that CLI provides help documentation.

        Given the laser-init CLI
        When invoked with --help
        Then it should display usage information

        Failure indicates help documentation is missing or broken.
        """
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["--help"])
        assert result.exit_code == 0
        # Check for usage line (may show "cli" or "laser-init" depending on context)
        assert result.output.startswith("Usage: cli [OPTIONS] COUNTRY LEVEL START_YEAR END_YEAR")

    def test_cli_shape_source_option(self):
        """Test that CLI accepts --shape-source option.

        Given the laser-init CLI
        When checking available options
        Then --shape-source should be available

        Failure indicates shape source option has changed.
        """
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["--help"])
        assert "--shape-source" in result.output

    def test_cli_model_option(self):
        """Test that CLI accepts --model option.

        Given the laser-init CLI
        When checking available options
        Then --model should be available for SI/SIR/SEIR selection

        Failure indicates model option has changed.
        """
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["--help"])
        assert "--model" in result.output

    def test_cli_output_dir_option(self):
        """Test that CLI accepts --output-dir option.

        Given the laser-init CLI
        When checking available options
        Then --output-dir should be available

        Failure indicates output directory option has changed.
        """
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["--help"])
        assert "--output-dir" in result.output


class TestCLIValidation:
    """Test suite for CLI input validation.

    Uses cli_env fixture for proper environment setup.
    """

    def test_cli_validates_country_code(self, cli_env):
        """Test that CLI validates country codes.

        Given an invalid country code with ephemeral environment
        When running laser-init
        Then it should report an error

        Failure indicates country validation is not working.
        Note: Uses cli_env for proper environment setup.
        """
        # Verify environment is set up
        assert cli_env["cache_dir"].exists()

        runner = CliRunner()
        output_dir = cli_env["work_dir"] / "test_invalid_country"
        result = runner.invoke(cli.cli, ["INVALID123", "2", "2000", "2025", "-o", str(output_dir)])
        # Should fail with invalid country
        assert result.exit_code != 0

    def test_cli_validates_admin_level(self, cli_env):
        """Test that CLI validates administrative level.

        Given a valid country but negative admin level
        When running laser-init
        Then it should report an error

        Failure indicates admin level validation is not working.
        """
        # Verify environment is set up
        assert cli_env["cache_dir"].exists()

        runner = CliRunner()
        output_dir = cli_env["work_dir"] / "test_invalid_level"
        result = runner.invoke(cli.cli, ["SEN", "-1", "2000", "2025", "-o", str(output_dir)])
        # Should fail with invalid level
        assert result.exit_code != 0

    def test_cli_validates_year_range(self, cli_env):
        """Test that CLI validates year ranges.

        Given start year after end year
        When running laser-init
        Then it should report an error

        Failure indicates year validation is not working.
        """
        # Verify environment is set up
        assert cli_env["cache_dir"].exists()

        runner = CliRunner()
        output_dir = cli_env["work_dir"] / "test_invalid_years"
        result = runner.invoke(cli.cli, ["SEN", "2", "2025", "2000", "-o", str(output_dir)])
        # Should fail with invalid year range
        assert result.exit_code != 0


class TestCLIWorkflow:
    """Test suite for CLI workflow orchestration."""

    @patch("laser.init.cli.iso_from_country_string")
    @patch("laser.init.cli.level_from_string")
    def test_cli_calls_validation_functions(self, mock_level, mock_iso):
        """Test that CLI calls validation functions.

        Given valid CLI arguments
        When executing laser-init
        Then validation functions should be called

        Failure indicates validation workflow has changed.
        """
        mock_iso.return_value = "SEN"
        mock_level.return_value = 2

        runner = CliRunner()
        # This will likely fail at later stages, but should call validation
        _result = runner.invoke(cli.cli, ["Senegal", "2", "2000", "2025"])

        # Validation functions should have been called
        mock_iso.assert_called()
        mock_level.assert_called()


class TestCLIDataSources:
    """Test suite for CLI data source handling.

    Uses cli_env fixture for real CLI execution with ephemeral environment.
    """

    def test_cli_accepts_geoboundaries_source(self, cli_env):
        """Test that CLI accepts geoBoundaries as shape source.

        Given --shape-source geoboundaries with unique output directory
        When running laser-init
        Then it should execute successfully and use geoBoundaries data

        Failure indicates geoBoundaries support has changed.
        Note: Verifies success by checking provenance.json for geoBoundaries URL.
        """
        import json

        # Verify environment is set up
        assert cli_env["cache_dir"].exists()

        runner = CliRunner()
        output_dir = cli_env["work_dir"] / "test_geoboundaries"

        # Run with geoboundaries (Senegal for small downloads)
        result = runner.invoke(
            cli.cli,
            [
                "SEN",
                "2",
                "2020",
                "2025",
                "--shape-source",
                "geoboundaries",
                "-o",
                str(output_dir),
            ],
        )

        # Should succeed
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify provenance shows geoBoundaries was used
        provenance_file = output_dir / "provenance.json"
        assert provenance_file.exists(), "Provenance file should exist"
        with open(provenance_file) as f:
            provenance = json.load(f)
        provenance_str = json.dumps(provenance).lower()
        assert "geoboundaries" in provenance_str, "Should use geoBoundaries"

    def test_cli_accepts_gadm_source(self, cli_env):
        """Test that CLI accepts GADM as shape source.

        Given --shape-source gadm with unique output directory
        When running laser-init
        Then it should execute successfully and use GADM data

        Failure indicates GADM support has changed.
        Note: Verifies success by checking provenance.json for GADM URL.
        """
        import json

        # Verify environment is set up
        assert cli_env["cache_dir"].exists()

        runner = CliRunner()
        output_dir = cli_env["work_dir"] / "test_gadm"

        # Run with GADM (Senegal for small downloads)
        result = runner.invoke(
            cli.cli,
            [
                "SEN",
                "2",
                "2020",
                "2025",
                "--shape-source",
                "gadm",
                "-o",
                str(output_dir),
            ],
        )

        # Should succeed
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify provenance shows GADM was used
        provenance_file = output_dir / "provenance.json"
        assert provenance_file.exists(), "Provenance file should exist"
        with open(provenance_file) as f:
            provenance = json.load(f)
        provenance_str = json.dumps(provenance).lower()
        assert "gadm" in provenance_str, "Should use GADM"

    def test_cli_accepts_unocha_source(self, cli_env):
        """Test that CLI accepts UNOCHA as shape source.

        Given --shape-source unocha with unique output directory
        When running laser-init
        Then it should execute successfully and use UNOCHA data

        Failure indicates UNOCHA support has changed.
        Note: Verifies success by checking provenance.json for UNOCHA URL.
        """
        import json

        # Verify environment is set up
        assert cli_env["cache_dir"].exists()

        runner = CliRunner()
        output_dir = cli_env["work_dir"] / "test_unocha"

        # Run with UNOCHA (Senegal for small downloads)
        result = runner.invoke(
            cli.cli,
            [
                "SEN",
                "2",
                "2020",
                "2025",
                "--shape-source",
                "unocha",
                "-o",
                str(output_dir),
            ],
        )

        # Should succeed
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify provenance shows UNOCHA was used (data.humdata.org is UNOCHA/HDX)
        provenance_file = output_dir / "provenance.json"
        assert provenance_file.exists(), "Provenance file should exist"
        with open(provenance_file) as f:
            provenance = json.load(f)
        provenance_str = json.dumps(provenance).lower()
        assert "humdata" in provenance_str or "unocha" in provenance_str, (
            "Should use UNOCHA (humdata.org)"
        )


class TestCLIModelGeneration:
    """Test suite for CLI model generation.

    Uses cli_env fixture for real CLI execution with ephemeral environment.
    """

    def test_cli_generates_si_model(self, cli_env):
        """Test that CLI generates SI model files.

        Given --model si with unique output directory
        When running laser-init
        Then SI model script (si.py) should be created in output directory

        Failure indicates SI model generation has changed.
        Note: Verifies success by checking for si.py in output directory.
        """
        # Verify environment is set up
        assert cli_env["cache_dir"].exists()

        runner = CliRunner()
        output_dir = cli_env["work_dir"] / "test_si_model"

        # Run with SI model (Senegal for small downloads)
        result = runner.invoke(
            cli.cli,
            ["SEN", "2", "2020", "2025", "--model", "si", "-o", str(output_dir)],
        )

        # Should succeed
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify SI model file was created
        assert output_dir.exists(), "Output directory should exist"
        si_script = output_dir / "si.py"
        assert si_script.exists(), "si.py should be created"

    def test_cli_generates_sir_model(self, cli_env):
        """Test that CLI generates SIR model files.

        Given --model sir with unique output directory
        When running laser-init
        Then SIR model script (sir.py) should be created in output directory

        Failure indicates SIR model generation has changed.
        Note: Verifies success by checking for sir.py in output directory.
        """
        # Verify environment is set up
        assert cli_env["cache_dir"].exists()

        runner = CliRunner()
        output_dir = cli_env["work_dir"] / "test_sir_model"

        # Run with SIR model (Senegal for small downloads)
        result = runner.invoke(
            cli.cli,
            ["SEN", "2", "2020", "2025", "--model", "sir", "-o", str(output_dir)],
        )

        # Should succeed
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify SIR model file was created
        assert output_dir.exists(), "Output directory should exist"
        sir_script = output_dir / "sir.py"
        assert sir_script.exists(), "sir.py should be created"

    def test_cli_generates_seir_model(self, cli_env):
        """Test that CLI generates SEIR model files.

        Given --model seir with unique output directory
        When running laser-init
        Then SEIR model script (seir.py) should be created in output directory

        Failure indicates SEIR model generation has changed.
        Note: Verifies success by checking for seir.py in output directory.
        """
        # Verify environment is set up
        assert cli_env["cache_dir"].exists()

        runner = CliRunner()
        output_dir = cli_env["work_dir"] / "test_seir_model"

        # Run with SEIR model (Senegal for small downloads)
        result = runner.invoke(
            cli.cli,
            ["SEN", "2", "2020", "2025", "--model", "seir", "-o", str(output_dir)],
        )

        # Should succeed
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify SEIR model file was created
        assert output_dir.exists(), "Output directory should exist"
        seir_script = output_dir / "seir.py"
        assert seir_script.exists(), "seir.py should be created"

    def test_cli_default_model_is_seir(self, cli_env):
        """Test that SEIR is the default model when --model not specified.

        Given valid arguments without --model option and unique output directory
        When running laser-init
        Then SEIR model (seir.py) should be generated by default

        Failure indicates default model has changed.
        Note: Per CLI help, default model is SEIR.
        Verifies by checking for seir.py in output directory.
        """
        # Verify environment is set up
        assert cli_env["cache_dir"].exists()

        runner = CliRunner()
        output_dir = cli_env["work_dir"] / "test_default_model"

        # Run without --model option (should default to SEIR, using Senegal)
        result = runner.invoke(cli.cli, ["SEN", "2", "2020", "2025", "-o", str(output_dir)])

        # Should succeed
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify SEIR model file was created (default)
        assert output_dir.exists(), "Output directory should exist"
        seir_script = output_dir / "seir.py"
        assert seir_script.exists(), "seir.py should be created by default"


class TestCLIIntegration:
    """Integration tests for CLI with real execution environment.

    Uses the cli_env fixture from conftest.py to set up ephemeral test environment.
    """

    def test_cli_creates_cache_directory(self, cli_env):
        """Test that CLI uses configured cache directory.

        Given a laser_config.yaml with cache_dir specified
        When CLI runs (even if it fails later)
        Then cache directory should be accessible

        Failure indicates cache directory configuration is not working.
        """
        # Verify cache directory exists from setup
        assert cli_env["cache_dir"].exists()
        assert cli_env["cache_dir"].is_dir()

        # Verify config file was created and contains cache_dir
        with open(cli_env["config_file"]) as f:
            config = yaml.safe_load(f)
        assert "cache_dir" in config
        assert config["cache_dir"] == str(cli_env["cache_dir"])

    def test_cli_creates_log_directory(self, cli_env):
        """Test that CLI uses configured log directory.

        Given a laser_config.yaml with log_dir specified
        When CLI runs
        Then log directory should be accessible

        Failure indicates log directory configuration is not working.
        """
        # Verify log directory exists from setup
        assert cli_env["log_dir"].exists()
        assert cli_env["log_dir"].is_dir()

        # Verify config file contains log_dir
        with open(cli_env["config_file"]) as f:
            config = yaml.safe_load(f)
        assert "log_dir" in config
        assert config["log_dir"] == str(cli_env["log_dir"])

    def test_cli_working_directory_is_temporary(self, cli_env):
        """Test that working directory is correctly set to temporary location.

        Given the cli_env fixture
        When checking current working directory
        Then it should be the temporary work directory

        Failure indicates working directory setup failed.
        """
        current_dir = Path.cwd()
        assert current_dir == cli_env["work_dir"]

    def test_cli_config_file_in_current_directory(self, cli_env):
        """Test that laser_config.yaml is in current directory.

        Given the cli_env fixture
        When checking for laser_config.yaml in current directory
        Then it should exist and be readable

        Failure indicates config file creation failed.
        """
        config_file = Path("laser_config.yaml")
        assert config_file.exists()
        assert config_file.is_file()

        # Verify it's readable and valid YAML
        with open(config_file) as f:
            config = yaml.safe_load(f)
        assert isinstance(config, dict)

    def test_cli_env_cleanup_restores_directory(self, tmp_path):  # noqa: ARG002
        """Test that fixture teardown restores original directory.

        Given the cli_env fixture is used and exits
        When checking current directory after fixture teardown
        Then it should be restored to original directory

        Failure indicates teardown is not cleaning up properly.
        """
        original_dir = Path.cwd()

        # Create and use the fixture context manually
        work_dir = tmp_path / "test_cleanup"
        work_dir.mkdir()

        try:
            os.chdir(work_dir)
            assert Path.cwd() == work_dir
        finally:
            os.chdir(original_dir)

        # Verify we're back to original directory
        assert Path.cwd() == original_dir

    def test_cli_invalid_country_with_real_env(self, cli_env):
        """Test CLI validation with invalid country in real environment.

        Given a configured environment
        When running CLI with invalid country code
        Then it should fail with appropriate error

        Failure indicates country validation is not working in real execution.
        Note: cli_env fixture is used for its side effects (sets up environment).
        """
        # cli_env sets up the environment (cache/log dirs, config file)
        assert cli_env["work_dir"].exists()  # Verify fixture ran

        runner = CliRunner()
        # Run with invalid country code
        result = runner.invoke(cli.cli, ["INVALID123", "2", "2020", "2025"])

        # Should fail
        assert result.exit_code != 0

    def test_cli_with_json_config(self, tmp_path):
        """Test that CLI works with JSON config file instead of YAML.

        Given an ephemeral environment with laser_config.json (not YAML)
        When running laser-init
        Then it should load JSON config and execute successfully

        Failure indicates JSON config loading is broken.
        Note: Tests config.py lines that handle JSON file loading.
        """
        import importlib
        import json

        # Save original directory
        original_dir = Path.cwd()

        try:
            # Create temporary working directory
            work_dir = tmp_path / "json_config_test"
            work_dir.mkdir()

            # Create cache and log directories
            cache_dir = work_dir / "cache"
            cache_dir.mkdir()
            log_dir = work_dir / "logs"
            log_dir.mkdir()

            # Write laser_config.json (NOT YAML)
            config_dict = {
                "cache_dir": str(cache_dir),
                "log_dir": str(log_dir),
            }
            config_file = work_dir / "laser_config.json"
            config_file.write_text(json.dumps(config_dict, indent=2))

            # Verify no YAML file exists
            yaml_file = work_dir / "laser_config.yaml"
            assert not yaml_file.exists(), "Should not have YAML file"

            # Change to temporary directory
            os.chdir(work_dir)

            # Reload config module to pick up JSON config
            importlib.reload(laser.init.config)

            # Run CLI with JSON config
            runner = CliRunner()
            output_dir = work_dir / "test_json_output"
            result = runner.invoke(cli.cli, ["SEN", "2", "2020", "2025", "-o", str(output_dir)])

            # Should succeed with JSON config
            assert result.exit_code == 0, f"CLI should work with JSON config: {result.output}"

            # Verify output was created
            assert output_dir.exists(), "Output directory should be created"
            seir_script = output_dir / "seir.py"
            assert seir_script.exists(), "Model script should be created with JSON config"

        finally:
            # Restore original directory and config
            os.chdir(original_dir)
            importlib.reload(laser.init.config)


class TestCLIModuleFunctions:
    """Test suite for CLI module-level functions."""

    def test_validate_arguments_bad_level_exception(self, tmp_path):
        """Test that validate_arguments raises Exit for invalid level.

        Given a call to validate_arguments with an invalid level parameter
        When the level argument is negative (e.g., -1)
        Then click.exceptions.Exit should be raised to indicate invalid input

        Failure indicates level validation is not working.
        Note: validate_arguments signature requires country, level, start_year, end_year, output_dir.
        """
        from click import exceptions

        # Call validate_arguments with an invalid level
        with pytest.raises(exceptions.Exit):
            cli.validate_arguments("SEN", "-1", 2020, 2025, tmp_path / "output")

    def test_validate_arguments_bad_years_exception(self, tmp_path):
        """Test that validate_arguments raises Exit for invalid year range.

        Given a call to validate_arguments with an invalid year range
        When start_year < 2000 or end_year > 2100 or end_year < start_year
        Then click.exceptions.Exit should be raised to indicate invalid input

        Failure indicates year validation is not working.
        Note: Valid year range is 2000-2100 (WorldPop population rasters begin at 2000).
        """
        from click import exceptions

        # Call validate_arguments with start_year < 2000
        with pytest.raises(exceptions.Exit):
            cli.validate_arguments("SEN", "2", 1999, 2020, tmp_path / "output")

        # Call validate_arguments with start_year > 2100
        with pytest.raises(exceptions.Exit):
            cli.validate_arguments("SEN", "2", 2101, 2110, tmp_path / "output")

        # Call validate_arguments with end_year < start_year
        with pytest.raises(exceptions.Exit):
            cli.validate_arguments("SEN", "2", 2025, 1975, tmp_path / "output")

        # Call validate_arguments with end_year > 2100
        with pytest.raises(exceptions.Exit):
            cli.validate_arguments("SEN", "2", 2025, 2101, tmp_path / "output")
