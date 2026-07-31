"""Tests for laser.init.models modules.

This module tests model template generation for SI, SIR, SEIR, and Measles
epidemiological models.
"""

from laser.init.models import measles, measles_plot, plot, seir, si, sir


class TestModelModulesExist:
    """Test suite for model module existence."""

    def test_si_model_module_exists(self):
        """Test that SI model module exists.

        Given the models package
        When checking for SI module
        Then it should be available

        Failure indicates SI model has been removed or renamed.
        """
        assert si is not None

    def test_sir_model_module_exists(self):
        """Test that SIR model module exists.

        Given the models package
        When checking for SIR module
        Then it should be available

        Failure indicates SIR model has been removed or renamed.
        """
        assert sir is not None

    def test_seir_model_module_exists(self):
        """Test that SEIR model module exists.

        Given the models package
        When checking for SEIR module
        Then it should be available

        Failure indicates SEIR model has been removed or renamed.
        """
        assert seir is not None

    def test_plot_module_exists(self):
        """Test that plot utilities module exists.

        Given the models package
        When checking for plot module
        Then it should be available

        Failure indicates plot module has been removed or renamed.
        """
        assert plot is not None

    def test_measles_model_module_exists(self):
        """Test that measles model module exists.

        Given the models package
        When checking for measles module
        Then it should be available

        Failure indicates measles model has been removed or renamed.
        """
        assert measles is not None

    def test_measles_plot_module_exists(self):
        """Test that measles_plot utilities module exists.

        Given the models package
        When checking for measles_plot module
        Then it should be available

        Failure indicates measles_plot module has been removed or renamed.
        """
        assert measles_plot is not None
