"""Central registry of pluggable pipeline components.

This module is the single source of truth mapping source/mode names (as accepted
on the command line and in configuration) to the component classes that implement
them. The CLI dispatches through these registries instead of repeating literal
``{name: Class}`` dictionaries at each call site, so a source is declared exactly
once and the extractor/transformer for a shape source cannot drift apart.

To add a new data source, implement the relevant Protocol(s) from
[`laser.init.interfaces`][laser.init.interfaces] and add a single entry to the
appropriate registry below.
"""

from dataclasses import dataclass

from .extractors.gadm import GadmExtractor
from .extractors.geoboundaries import GeoBoundariesExtractor
from .extractors.unocha import UnochaExtractor
from .extractors.unwpp import UnwppExtractor
from .extractors.worldpop import WorldPopExtractor
from .interfaces import (
    ModelLoader,
    RasterExtractor,
    ShapeExtractor,
    ShapeTransformer,
    StatsExtractor,
    StatsTransformer,
)
from .loaders.abm import AbmLoader
from .loaders.mpm import MpmLoader
from .transformers.gadm import GadmTransformer
from .transformers.geoboundaries import GeoBoundariesTransformer
from .transformers.unocha import UnochaTransformer
from .transformers.unwpp import UnwppTransformer


@dataclass(frozen=True)
class ShapeSource:
    """Pairs the extractor and transformer that together handle a shape source."""

    extractor: type[ShapeExtractor]
    transformer: type[ShapeTransformer]


@dataclass(frozen=True)
class StatsSource:
    """Pairs the extractor and transformer that together handle a stats source."""

    extractor: type[StatsExtractor]
    transformer: type[StatsTransformer]


# Administrative-boundary shape sources (CLI --shape-source).
SHAPE_SOURCES: dict[str, ShapeSource] = {
    "unocha": ShapeSource(UnochaExtractor, UnochaTransformer),
    "geoboundaries": ShapeSource(GeoBoundariesExtractor, GeoBoundariesTransformer),
    "gadm": ShapeSource(GadmExtractor, GadmTransformer),
}

# Population raster sources (CLI --raster-source).
RASTER_SOURCES: dict[str, type[RasterExtractor]] = {
    "worldpop": WorldPopExtractor,
}

# Demographic statistics sources (CLI --stats-source).
STATS_SOURCES: dict[str, StatsSource] = {
    "unwpp": StatsSource(UnwppExtractor, UnwppTransformer),
}

# Model-script loaders, keyed by modeling mode (CLI --mode).
MODEL_LOADERS: dict[str, type[ModelLoader]] = {
    "abm": AbmLoader,
    "mpm": MpmLoader,
}


def _lookup(registry: dict, key: str, kind: str):
    """Return ``registry[key.lower()]`` or raise a clear KeyError.

    Args:
        registry: The registry dictionary to look up in.
        key: The source/mode name (case-insensitive).
        kind: Human-readable name of the registry (for the error message).

    Returns:
        The registered value for ``key``.

    Raises:
        KeyError: If ``key`` is not registered; the message lists valid options.
    """
    normalized = (key or "").lower()
    try:
        return registry[normalized]
    except KeyError:
        valid = ", ".join(sorted(registry))
        raise KeyError(f"Invalid {kind} '{key}'. Valid options are: {valid}.") from None


def get_shape_source(name: str) -> ShapeSource:
    """Return the [`ShapeSource`][laser.init.registry.ShapeSource] for ``name``.

    Raises:
        KeyError: If ``name`` is not a registered shape source.
    """
    return _lookup(SHAPE_SOURCES, name, "shape source")


def get_raster_extractor(name: str) -> type[RasterExtractor]:
    """Return the raster extractor class for ``name``.

    Raises:
        KeyError: If ``name`` is not a registered raster source.
    """
    return _lookup(RASTER_SOURCES, name, "raster source")


def get_stats_source(name: str) -> StatsSource:
    """Return the [`StatsSource`][laser.init.registry.StatsSource] for ``name``.

    Raises:
        KeyError: If ``name`` is not a registered stats source.
    """
    return _lookup(STATS_SOURCES, name, "demographic stats source")


def get_model_loader(mode: str) -> type[ModelLoader]:
    """Return the model loader class for the modeling ``mode`` (e.g. "ABM").

    Raises:
        KeyError: If ``mode`` is not a registered modeling mode.
    """
    return _lookup(MODEL_LOADERS, mode, "modeling mode")
