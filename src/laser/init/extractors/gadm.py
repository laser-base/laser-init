"""
Docstring for laser.init.extractors.gadm

https://geodata.ucdavis.edu/gadm/gadm4.1/gpkg/gadm41_NGA.gpkg
https://geodata.ucdavis.edu/gadm/gadm4.1/shp/gadm41_NGA_shp.zip
"""

from pathlib import Path

from ..config import configuration as config
from ..config import default_cache_directory
from ..utils import download_file, error, inform


class GadmExtractor:
    def __init__(self, prefer_gpkg: bool = False) -> None:
        """Initialize the GADM extractor.

        Args:
            prefer_gpkg: If True, prefer downloading GeoPackage format over shapefile format.
                Defaults to False (prefers shapefile).

        Returns:
            None
        """
        self.prefer_gpkg = prefer_gpkg

        return

    @staticmethod
    def description() -> str:
        """Return a brief description of this extractor.

        Returns:
            A string describing the data source and purpose of this extractor.
        """
        return "Extracts data from the Global Administrative Areas (GADM) at https://geodata.ucdavis.edu/gadm"

    def extract(self, country: str, level: int, year: int) -> Path | None:
        """Extract GADM administrative boundary data for a country.

        Downloads either shapefile (zip) or geopackage format administrative boundary
        data from GADM for the specified country. Files are cached locally to avoid
        redundant downloads.

        Args:
            country: ISO 3166-1 alpha-3 country code (e.g., "NGA" for Nigeria).
            level: Administrative level (0=country, 1=regions, 2=districts, etc.).
            year: Year parameter (currently unused - GADM provides latest version only).

        Returns:
            Path to the downloaded file (zip or gpkg), or None if download failed.

        Raises:
            RuntimeError: If both shapefile and geopackage downloads fail.
        """

        cache_root = Path(config.get("cache_dir", default_cache_directory))
        gadm_path = Path("gadm") / country
        (cache_root / gadm_path).mkdir(parents=True, exist_ok=True)

        local_path = None
        downloaded = False

        # Try the geopackage first, then fall back to shapefile if it's not found
        if not self.prefer_gpkg:
            shp_zip = f"gadm41_{country}_shp.zip"
            url = f"https://geodata.ucdavis.edu/gadm/gadm4.1/shp/{shp_zip}"

            try:
                local_path = download_file(url, cache_dir=cache_root, dest_dir=gadm_path)
                inform(f"Downloaded GADM shapefile zip: {local_path}")

                downloaded = True

            except Exception as e:
                inform(f"Failed to download GADM shapefile: {e}. Trying geopackage.")
                downloaded = False
                local_path = None

        if not downloaded:
            gpkg = f"gadm41_{country}.gpkg"
            url = f"https://geodata.ucdavis.edu/gadm/gadm4.1/gpkg/{gpkg}"

            try:
                local_path = download_file(url, cache_dir=cache_root, dest_dir=gadm_path)
                inform(f"Downloaded GADM geopackage: {local_path}")
                downloaded = True

            except Exception as e:
                error(f"Failed to download GADM geopackage: {e}.", RuntimeError)

        return local_path
