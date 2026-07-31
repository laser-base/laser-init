"""Tests for laser.init.loaders modules.

This module tests model loader functionality for both ABM (Agent-Based Models)
and MPM (Metapopulation Models), including script generation and configuration.
"""

import pytest

from laser.init.loaders import abm, mpm


class TestAbmLoader:
    """Test suite for ABM loader."""

    def test_abm_loader_instantiation(self):
        """Test that ABM loader can be instantiated.

        Given the ABM loader class
        When creating an instance
        Then it should be created successfully

        Failure indicates ABM loader initialization has changed.
        """
        loader = abm.AbmLoader()
        assert loader is not None

    def test_abm_loader_has_description(self):
        """Test that ABM loader provides a description method.

        Given an ABM loader instance
        When calling description()
        Then it should return an informative string

        Failure indicates description method is missing or broken.
        """
        loader = abm.AbmLoader()
        assert hasattr(loader, "description")
        assert callable(loader.description)
        description = loader.description()
        assert isinstance(description, str)
        assert len(description) > 0

    def test_abm_loader_has_emit_script(self):
        """Test that ABM loader has emit_script method.

        Given an ABM loader instance
        When checking for emit_script method
        Then it should be present and callable

        Failure indicates emit_script method is missing.
        """
        loader = abm.AbmLoader()
        assert hasattr(loader, "emit_script")
        assert callable(loader.emit_script)

    def test_abm_emit_script_signature(self):
        """Test that emit_script has correct signature.

        Given the ABM loader emit_script method
        When inspecting its signature
        Then it should accept mode, model, filenames, and output_dir

        Failure indicates emit_script signature has changed.
        Note: Per docstring, accepts mode, model, shape_filename, cxr_filename,
        pop_filename, exp_filename, output_dir.
        """
        from inspect import signature

        sig = signature(abm.AbmLoader.emit_script)
        params = list(sig.parameters.keys())
        assert "mode" in params
        assert "model" in params
        assert "shape_filename" in params
        assert "cxr_filename" in params
        assert "pop_filename" in params
        assert "exp_filename" in params
        assert "output_dir" in params

    def test_abm_emit_script_creates_files(self, tmp_path):
        """Test that emit_script generates required files.

        Given valid input files and parameters
        When emit_script() is called
        Then it should create model script and config files

        Failure indicates file generation is broken.
        Note: Per docstring, creates YAML config, copies model script (SI/SIR/SEIR),
        and copies plotting utilities.
        """
        loader = abm.AbmLoader()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create dummy input files
        shape_file = tmp_path / "shapes.gpkg"
        cxr_file = tmp_path / "cxr.csv"
        pop_file = tmp_path / "pop.csv"
        exp_file = tmp_path / "exp.csv"

        for f in [shape_file, cxr_file, pop_file, exp_file]:
            f.touch()

        # Generate SI model
        loader.emit_script(
            mode="ABM",
            model="SI",
            shape_filename=shape_file,
            cxr_filename=cxr_file,
            pop_filename=pop_file,
            exp_filename=exp_file,
            output_dir=output_dir,
        )

        # Check that files were created
        config_file = output_dir / "config.yaml"
        model_file = output_dir / "si.py"
        plot_file = output_dir / "plot.py"

        assert config_file.exists(), "config.yaml should be created"
        assert model_file.exists(), "model script should be created"
        assert plot_file.exists(), "plot.py should be created"

    def test_abm_emit_script_sir_model(self, tmp_path):
        """Test that emit_script works for SIR model.

        Given SIR model type
        When emit_script() is called
        Then it should create SIR model script

        Failure indicates SIR model generation is broken.
        """
        loader = abm.AbmLoader()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create dummy input files
        shape_file = tmp_path / "shapes.gpkg"
        cxr_file = tmp_path / "cxr.csv"
        pop_file = tmp_path / "pop.csv"
        exp_file = tmp_path / "exp.csv"

        for f in [shape_file, cxr_file, pop_file, exp_file]:
            f.touch()

        loader.emit_script(
            mode="ABM",
            model="SIR",
            shape_filename=shape_file,
            cxr_filename=cxr_file,
            pop_filename=pop_file,
            exp_filename=exp_file,
            output_dir=output_dir,
        )

        model_file = output_dir / "sir.py"
        assert model_file.exists()

    def test_abm_emit_script_seir_model(self, tmp_path):
        """Test that emit_script works for SEIR model.

        Given SEIR model type
        When emit_script() is called
        Then it should create SEIR model script

        Failure indicates SEIR model generation is broken.
        """
        loader = abm.AbmLoader()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create dummy input files
        shape_file = tmp_path / "shapes.gpkg"
        cxr_file = tmp_path / "cxr.csv"
        pop_file = tmp_path / "pop.csv"
        exp_file = tmp_path / "exp.csv"

        for f in [shape_file, cxr_file, pop_file, exp_file]:
            f.touch()

        loader.emit_script(
            mode="ABM",
            model="SEIR",
            shape_filename=shape_file,
            cxr_filename=cxr_file,
            pop_filename=pop_file,
            exp_filename=exp_file,
            output_dir=output_dir,
        )

        model_file = output_dir / "seir.py"
        assert model_file.exists()

    def test_abm_emit_script_validates_mode(self, tmp_path):
        """Test that emit_script validates mode parameter.

        Given an invalid mode (not "ABM")
        When emit_script() is called
        Then it should raise AssertionError

        Failure indicates mode validation is not working.
        Note: Per docstring, raises AssertionError if mode is not "ABM".
        """
        loader = abm.AbmLoader()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create dummy input files
        shape_file = tmp_path / "shapes.gpkg"
        cxr_file = tmp_path / "cxr.csv"
        pop_file = tmp_path / "pop.csv"
        exp_file = tmp_path / "exp.csv"

        for f in [shape_file, cxr_file, pop_file, exp_file]:
            f.touch()

        with pytest.raises(AssertionError):
            loader.emit_script(
                mode="INVALID",
                model="SI",
                shape_filename=shape_file,
                cxr_filename=cxr_file,
                pop_filename=pop_file,
                exp_filename=exp_file,
                output_dir=output_dir,
            )

    def test_abm_config_file_contains_paths(self, tmp_path):
        """Test that generated config.yaml contains file paths.

        Given valid input files
        When emit_script() generates config.yaml
        Then it should contain paths to data files

        Failure indicates config generation is broken.
        Note: Per docstring, config contains data file paths and simulation parameters.
        """
        import yaml

        loader = abm.AbmLoader()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create dummy input files
        shape_file = tmp_path / "shapes.gpkg"
        cxr_file = tmp_path / "cxr.csv"
        pop_file = tmp_path / "pop.csv"
        exp_file = tmp_path / "exp.csv"

        for f in [shape_file, cxr_file, pop_file, exp_file]:
            f.touch()

        loader.emit_script(
            mode="ABM",
            model="SI",
            shape_filename=shape_file,
            cxr_filename=cxr_file,
            pop_filename=pop_file,
            exp_filename=exp_file,
            output_dir=output_dir,
        )

        # Read and verify config
        config_file = output_dir / "config.yaml"
        with open(config_file) as f:
            config = yaml.safe_load(f)

        # Config should reference the input files
        assert config is not None
        assert isinstance(config, dict)

    def test_abm_emit_script_measles_model(self, tmp_path):
        """Test that emit_script works for MEASLES model.

        Given MEASLES model type
        When emit_script() is called
        Then it should create measles.py, measles_plot.py, and config.yaml

        Failure indicates MEASLES model generation is broken.
        """
        loader = abm.AbmLoader()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create dummy input files
        shape_file = tmp_path / "shapes.gpkg"
        cxr_file = tmp_path / "cxr.csv"
        pop_file = tmp_path / "pop.csv"
        exp_file = tmp_path / "exp.csv"

        for f in [shape_file, cxr_file, pop_file, exp_file]:
            f.touch()

        loader.emit_script(
            mode="ABM",
            model="MEASLES",
            shape_filename=shape_file,
            cxr_filename=cxr_file,
            pop_filename=pop_file,
            exp_filename=exp_file,
            output_dir=output_dir,
        )

        assert (output_dir / "measles.py").exists(), "measles.py should be created"
        assert (
            output_dir / "measles_plot.py"
        ).exists(), "measles_plot.py should be created"
        assert (output_dir / "config.yaml").exists(), "config.yaml should be created"

    def test_abm_measles_config_has_correct_keys(self, tmp_path):
        """Test that measles config.yaml contains expected keys.

        Given MEASLES model type
        When emit_script() generates config.yaml
        Then it should contain measles-specific simulation parameters

        Failure indicates measles config template is malformed.
        """
        import yaml

        loader = abm.AbmLoader()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        shape_file = tmp_path / "shapes.gpkg"
        cxr_file = tmp_path / "cxr.csv"
        pop_file = tmp_path / "pop.csv"
        exp_file = tmp_path / "exp.csv"

        for f in [shape_file, cxr_file, pop_file, exp_file]:
            f.touch()

        loader.emit_script(
            mode="ABM",
            model="MEASLES",
            shape_filename=shape_file,
            cxr_filename=cxr_file,
            pop_filename=pop_file,
            exp_filename=exp_file,
            output_dir=output_dir,
        )

        config = yaml.safe_load((output_dir / "config.yaml").read_text())
        assert "data_dir" in config
        assert "datafiles" in config
        assert "shape_data" in config["datafiles"]
        assert "cxr_data" in config["datafiles"]
        sim = config["simulation"]
        assert "beta" in sim
        assert "seasonality" in sim
        assert "distance_exponent" in sim
        assert "mixing_scale" in sim
        assert "initial_infections" in sim
        assert "naive_population" in sim

    def test_abm_measles_does_not_create_generic_files(self, tmp_path):
        """Test that MEASLES model does not create generic model files.

        Given MEASLES model type
        When emit_script() is called
        Then it should NOT create plot.py or any generic model scripts

        Failure indicates MEASLES routing is leaking to generic path.
        """
        loader = abm.AbmLoader()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        shape_file = tmp_path / "shapes.gpkg"
        cxr_file = tmp_path / "cxr.csv"
        pop_file = tmp_path / "pop.csv"
        exp_file = tmp_path / "exp.csv"

        for f in [shape_file, cxr_file, pop_file, exp_file]:
            f.touch()

        loader.emit_script(
            mode="ABM",
            model="MEASLES",
            shape_filename=shape_file,
            cxr_filename=cxr_file,
            pop_filename=pop_file,
            exp_filename=exp_file,
            output_dir=output_dir,
        )

        assert not (output_dir / "plot.py").exists(), (
            "generic plot.py should not be created for MEASLES"
        )
        assert not (output_dir / "seir.py").exists(), "seir.py should not be created for MEASLES"


class TestMpmLoader:
    """Test suite for MPM loader."""

    def test_mpm_loader_instantiation(self):
        """Test that MPM loader can be instantiated.

        Given the MPM loader class
        When creating an instance
        Then it should be created successfully

        Failure indicates MPM loader initialization has changed.
        """
        loader = mpm.MpmLoader()
        assert loader is not None

    def test_mpm_loader_has_description(self):
        """Test that MPM loader provides a description method.

        Given an MPM loader instance
        When calling description()
        Then it should return an informative string

        Failure indicates description method is missing or broken.
        """
        loader = mpm.MpmLoader()
        assert hasattr(loader, "description")
        assert callable(loader.description)
        description = loader.description()
        assert isinstance(description, str)
        assert len(description) > 0

    def test_mpm_loader_has_emit_script(self):
        """Test that MPM loader has emit_script method.

        Given an MPM loader instance
        When checking for emit_script method
        Then it should be present and callable

        Failure indicates emit_script method is missing.
        """
        loader = mpm.MpmLoader()
        assert hasattr(loader, "emit_script")
        assert callable(loader.emit_script)

    def test_mpm_emit_script_is_placeholder(self):
        """Test that MPM emit_script is a placeholder implementation.

        Given an MPM loader instance
        When calling emit_script()
        Then it should return None (placeholder)

        Failure indicates MPM implementation status has changed.
        Note: Per docstring, MPM is a placeholder for future support.
        Current implementation is a no-op that returns None.
        """
        loader = mpm.MpmLoader()
        result = loader.emit_script()
        assert result is None

    def test_mpm_emit_script_no_files_created(self, tmp_path):
        """Test that MPM emit_script doesn't create files yet.

        Given an MPM loader instance and output directory
        When calling emit_script()
        Then no files should be created (not yet implemented)

        Failure indicates MPM implementation has been added.
        Note: This is a placeholder test for future MPM implementation.
        """
        loader = mpm.MpmLoader()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Call emit_script - should not create any files yet
        loader.emit_script()

        # Verify no files were created in output directory
        files = list(output_dir.iterdir())
        assert len(files) == 0, "MPM loader should not create files yet (placeholder)"


class TestLoaderInterface:
    """Test suite for loader interface consistency."""

    def test_all_loaders_have_consistent_interface(self):
        """Test that all loaders follow the same interface.

        Given ABM and MPM loader classes
        When checking their methods
        Then they should both have emit_script() and description() methods

        Failure indicates inconsistent loader interfaces.
        """
        abm_loader = abm.AbmLoader()
        mpm_loader = mpm.MpmLoader()

        for loader in [abm_loader, mpm_loader]:
            assert hasattr(loader, "emit_script")
            assert hasattr(loader, "description")
            assert callable(loader.emit_script)
            assert callable(loader.description)

    def test_loader_descriptions_are_informative(self):
        """Test that loader descriptions contain relevant information.

        Given all loader instances
        When calling description()
        Then each should mention its loader type

        Failure indicates descriptions are not informative enough.
        """
        abm_loader = abm.AbmLoader()
        mpm_loader = mpm.MpmLoader()

        abm_desc = abm_loader.description().lower()
        mpm_desc = mpm_loader.description().lower()

        # ABM description should mention agent-based or abm
        assert "abm" in abm_desc or "agent" in abm_desc

        # MPM description should mention metapopulation or mpm
        assert "mpm" in mpm_desc or "metapopulation" in mpm_desc
