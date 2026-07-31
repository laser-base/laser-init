"""
Docstring for laser.init.extractors.unocha

Primary source: the laser-base UNOCHA repository, which provides per-country,
per-administrative-level GeoPackage files compressed with zstd. E.g.,
https://github.com/laser-base/unocha/raw/refs/heads/main/data/SEN/UNOCHA-SEN-ADM1.gpkg.zstd

Fallback source: the global administrative boundaries geodatabase from UNOCHA's
Humanitarian Data Exchange (HDX). E.g.,
https://data.humdata.org/dataset/70f1cb54-a30c-43b2-a751-44e77d8f5ade/resource/733a9d4c-4e70-4f67-a5af-4138922cf43f/download/global_admin_boundaries_matched_latest.gdb.zip
"""

from pathlib import Path

from ..config import configuration as config
from ..config import default_cache_directory
from ..utils import download_file, error, inform


class UnochaExtractor:
    """Extracts UNOCHA administrative boundary data from the laser-base UNOCHA repository.

    Boundary data is downloaded per-country and per-administrative-level from
    https://github.com/laser-base/unocha. If a country or level is not available
    in that repository, the extractor falls back to downloading the global
    administrative boundaries geodatabase from UNOCHA's Humanitarian Data Exchange.
    """

    # Base URL for per-country, per-level data in the laser-base UNOCHA repository.
    REPOSITORY_BASE_URL = "https://github.com/laser-base/unocha/raw/refs/heads/main/data"

    # Fallback: single global geodatabase from UNOCHA's Humanitarian Data Exchange (HDX).
    GLOBAL_GDB_FILE = "global_admin_boundaries_matched_latest.gdb.zip"
    GLOBAL_GDB_URL = (
        "https://data.humdata.org/dataset/70f1cb54-a30c-43b2-a751-44e77d8f5ade/"
        f"resource/733a9d4c-4e70-4f67-a5af-4138922cf43f/download/{GLOBAL_GDB_FILE}"
    )

    def __init__(self) -> None:
        """Initialize the UNOCHA extractor.

        Returns:
            None
        """
        pass

    @staticmethod
    def description() -> str:
        """Return a brief description of this extractor.

        Returns:
            A string describing the data source and purpose of this extractor.
        """
        return "Extracts data from the United Nations Office for the Coordination of Humanitarian Affairs (UNOCHA) at https://github.com/laser-base/unocha"

    def extract(self, country: str, level: int, year: int) -> Path | None:
        """Extract UNOCHA administrative boundary data for a country and level.

        Attempts to download the per-country, per-administrative-level GeoPackage
        (compressed with zstd) from the laser-base UNOCHA repository. If that data
        is unavailable (for example, the country or level is not published in the
        repository), the extractor falls back to downloading the single global
        administrative boundaries geodatabase from UNOCHA's Humanitarian Data
        Exchange, which is then filtered in the transform step.

        Args:
            country: ISO 3166-1 alpha-3 country code (e.g., "SEN" for Senegal).
            level: Administrative level (0=country, 1=first-level subdivisions, etc.).
            year: Year parameter (currently unused - the repository serves the
                latest published boundaries).

        Returns:
            Path to the downloaded file (a ``.gpkg.zstd`` from the repository, or the
            global ``.gdb.zip`` fallback), or None if all downloads failed.

        Raises:
            RuntimeError: If both the repository download and the global fallback
                download fail.
        """

        # Sample: https://github.com/laser-base/unocha/raw/refs/heads/main/data/SEN/UNOCHA-SEN-ADM1.gpkg.zstd

        cache_root = Path(config.get("cache_dir", default_cache_directory))
        unocha_path = Path("UNOCHA") / country
        (cache_root / unocha_path).mkdir(parents=True, exist_ok=True)

        gpkg_file = f"UNOCHA-{country}-ADM{level}.gpkg.zstd"
        url = f"{self.REPOSITORY_BASE_URL}/{country}/{gpkg_file}"

        try:
            local_path = download_file(url, cache_dir=cache_root, dest_dir=unocha_path)
            inform(f"Downloaded UNOCHA data: {local_path}")
            return local_path

        except Exception as e:
            inform(
                f"UNOCHA repository data unavailable for {country} ADM{level} ({e}); "
                "falling back to the global UNOCHA/HDX dataset."
            )
            return self._extract_global_fallback(cache_root)

    def _extract_global_fallback(self, cache_root: Path) -> Path | None:
        """Download the global UNOCHA administrative boundaries geodatabase.

        This reproduces the original UNOCHA extractor behavior: a single global
        geodatabase zip file containing all countries, which is filtered by country
        and administrative level in the transform step.

        Args:
            cache_root: The root cache directory where the file will be stored.

        Returns:
            Path to the downloaded global geodatabase zip file, or None if the
            download failed.

        Raises:
            RuntimeError: If the download fails.
        """

        unocha_path = Path("UNOCHA")
        (cache_root / unocha_path).mkdir(parents=True, exist_ok=True)

        local_path = None

        try:
            local_path = download_file(
                self.GLOBAL_GDB_URL, cache_dir=cache_root, dest_dir=unocha_path
            )
            inform(f"Downloaded UNOCHA global fallback data: {local_path}")

        except Exception as e:
            error(f"Failed to download UNOCHA data: {e}.", RuntimeError)

        return local_path
