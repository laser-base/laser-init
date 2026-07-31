"""Structural interface definitions for the laser-init data pipeline.

The pipeline is built from pluggable components in three families — extractors
(download raw data), transformers (convert raw data to model-ready files), and
loaders (emit model scripts). Each family is described here as a
[`typing.Protocol`][typing.Protocol] rather than an abstract base class because:

- The components are stateless and duck-typed; there is no shared implementation
  to inherit, so an ABC would add an empty base with no behavior.
- Extractors genuinely differ by role — shape extractors take an admin level,
  raster extractors take a single year, and stats extractors take a year range —
  so no single inheritance hierarchy fits all of them. Structural typing models
  these distinct contracts without forcing a common base.
- Existing components already satisfy these contracts without modification, and
  the test suite verifies conformance structurally.

The protocols are `runtime_checkable`, so `isinstance(obj, ShapeExtractor)` works
for defensive checks and tests (note: that only verifies method *presence*; a
static type checker such as mypy additionally verifies the method *signatures*).

These protocols are the contract to implement when adding a new data source; see
[`laser.init.registry`][laser.init.registry] for where implementations are
registered.
"""

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class ShapeExtractor(Protocol):
    """Downloads administrative-boundary shape data for a country and level."""

    def description(self) -> str:
        """Return a brief description of the data source."""
        ...

    def extract(self, country: str, level: int, year: int) -> Path | None:
        """Download shape data and return the local path (or None on failure)."""
        ...


@runtime_checkable
class RasterExtractor(Protocol):
    """Downloads a population raster for a country and year."""

    def description(self) -> str:
        """Return a brief description of the data source."""
        ...

    def extract(self, country: str, year: int) -> Path | None:
        """Download the raster and return the local path (or None on failure)."""
        ...


@runtime_checkable
class StatsExtractor(Protocol):
    """Downloads demographic statistics for a country over a year range."""

    def description(self) -> str:
        """Return a brief description of the data source."""
        ...

    def extract(self, country: str, start_year: int, end_year: int) -> tuple[Path, ...]:
        """Download stats files and return their local paths."""
        ...


@runtime_checkable
class ShapeTransformer(Protocol):
    """Filters shape data by country/level and joins it with population."""

    def description(self) -> str:
        """Return a brief description of the transformation."""
        ...

    def transform(
        self,
        shape_file: Path,
        iso_code: str,
        adm_level: int,
        raster_file: Path,
        output_dir: Path,
    ) -> Path:
        """Transform shape data into a model-ready GeoPackage and return its path."""
        ...


@runtime_checkable
class StatsTransformer(Protocol):
    """Filters demographic statistics by country and year range."""

    def description(self) -> str:
        """Return a brief description of the transformation."""
        ...

    def transform(
        self,
        stats_data: tuple[Path, ...],
        iso_code: str,
        start_year: int,
        end_year: int,
        output_dir: Path,
    ) -> tuple[Path, Path, Path]:
        """Transform stats data into model-ready CSV files and return their paths."""
        ...


@runtime_checkable
class ModelLoader(Protocol):
    """Emits a runnable model script and configuration for a given mode/model."""

    def description(self) -> str:
        """Return a brief description of the loader."""
        ...

    def emit_script(
        self,
        mode: str,
        model: str,
        shape_filename: Path,
        cxr_filename: Path,
        pop_filename: Path,
        exp_filename: Path,
        output_dir: Path,
    ) -> None:
        """Write the model script and configuration into ``output_dir``."""
        ...
