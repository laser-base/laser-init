"""Tests for laser.init.registry and laser.init.interfaces.

These tests verify the central component registry and the structural contracts
(Protocols) that pipeline components must satisfy. Failure indicates that a data
source has drifted from its interface, that the registry and CLI options have
fallen out of sync, or that registry lookup/error behavior has changed.
"""

import pytest

from laser.init import interfaces, registry
from laser.init.cli import cli


def _cli_choice_options(param_name: str) -> set[str]:
    """Return the set of click.Choice options declared for a CLI parameter.

    Args:
        param_name: The destination name of the CLI parameter (e.g. "shape_source").

    Returns:
        The set of valid choice strings for that parameter.
    """
    for param in cli.params:
        if param.name == param_name:
            return set(param.type.choices)
    raise AssertionError(f"CLI parameter '{param_name}' not found.")


class TestInterfaceConformance:
    """Every registered component must satisfy its declared Protocol.

    Failure means a component is missing a contract method (e.g. description,
    extract, transform, emit_script) that the pipeline relies on.
    """

    def test_shape_sources_conform_to_protocols(self):
        """Given each registered shape source, when instantiated, then the extractor
        and transformer satisfy the ShapeExtractor/ShapeTransformer protocols."""
        for name, source in registry.SHAPE_SOURCES.items():
            assert isinstance(source.extractor(), interfaces.ShapeExtractor), name
            assert isinstance(source.transformer(), interfaces.ShapeTransformer), name

    def test_raster_extractors_conform_to_protocol(self):
        """Given each registered raster source, when instantiated, then it satisfies
        the RasterExtractor protocol."""
        for name, extractor in registry.RASTER_SOURCES.items():
            assert isinstance(extractor(), interfaces.RasterExtractor), name

    def test_stats_sources_conform_to_protocols(self):
        """Given each registered stats source, when instantiated, then the extractor
        and transformer satisfy the StatsExtractor/StatsTransformer protocols."""
        for name, source in registry.STATS_SOURCES.items():
            assert isinstance(source.extractor(), interfaces.StatsExtractor), name
            assert isinstance(source.transformer(), interfaces.StatsTransformer), name

    def test_model_loaders_conform_to_protocol(self):
        """Given each registered model loader, when instantiated, then it satisfies
        the ModelLoader protocol."""
        for name, loader in registry.MODEL_LOADERS.items():
            assert isinstance(loader(), interfaces.ModelLoader), name


class TestRegistryCliConsistency:
    """The registry and the CLI's accepted options must not drift apart.

    Failure means the CLI advertises a source/mode the registry cannot resolve
    (or vice versa), which would surface as a runtime error for users.
    """

    def test_shape_sources_match_cli_choices(self):
        """Given the --shape-source CLI choices, then they exactly match the
        SHAPE_SOURCES registry keys."""
        assert set(registry.SHAPE_SOURCES) == _cli_choice_options("shape_source")

    def test_raster_sources_match_cli_choices(self):
        """Given the --raster-source CLI choices, then they exactly match the
        RASTER_SOURCES registry keys."""
        assert set(registry.RASTER_SOURCES) == _cli_choice_options("raster_source")

    def test_stats_sources_match_cli_choices(self):
        """Given the --stats-source CLI choices, then they exactly match the
        STATS_SOURCES registry keys."""
        assert set(registry.STATS_SOURCES) == _cli_choice_options("stats_source")

    def test_model_loaders_match_cli_mode_choices(self):
        """Given the --mode CLI choices (case-insensitive), then they exactly match
        the MODEL_LOADERS registry keys."""
        modes = {choice.lower() for choice in _cli_choice_options("mode")}
        assert set(registry.MODEL_LOADERS) == modes


class TestRegistryLookups:
    """Lookup helpers resolve case-insensitively and fail with a clear message."""

    def test_get_shape_source_is_case_insensitive(self):
        """Given a mixed-case shape source name, when looked up, then it resolves to
        the registered ShapeSource."""
        assert registry.get_shape_source("UNOCHA") is registry.SHAPE_SOURCES["unocha"]

    def test_get_model_loader_is_case_insensitive(self):
        """Given a mixed-case mode, when looked up, then it resolves to the registered
        loader class."""
        assert registry.get_model_loader("ABM") is registry.MODEL_LOADERS["abm"]

    def test_get_shape_source_unknown_raises_with_options(self):
        """Given an unregistered shape source, when looked up, then KeyError is raised
        and the message lists the valid options."""
        with pytest.raises(KeyError) as excinfo:
            registry.get_shape_source("does-not-exist")
        message = str(excinfo.value)
        assert "Valid options are" in message
        assert "unocha" in message

    def test_get_raster_extractor_unknown_raises(self):
        """Given an unregistered raster source, when looked up, then KeyError is raised."""
        with pytest.raises(KeyError):
            registry.get_raster_extractor("nope")

    def test_get_stats_source_unknown_raises(self):
        """Given an unregistered stats source, when looked up, then KeyError is raised."""
        with pytest.raises(KeyError):
            registry.get_stats_source("nope")

    def test_get_model_loader_unknown_raises(self):
        """Given an unregistered mode, when looked up, then KeyError is raised."""
        with pytest.raises(KeyError):
            registry.get_model_loader("nope")
