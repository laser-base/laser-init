"""
UNOCHA data transformer.

Handles two UNOCHA shape data formats:

- The per-country, per-administrative-level GeoPackage files (``.gpkg.zstd``) served
  by the laser-base UNOCHA repository. These are zstd-compressed, already scoped to a
  single country and level, and require only decompression and column normalization.
- The single global geodatabase (``.gdb.zip``) from UNOCHA's Humanitarian Data Exchange,
  used as a fallback. This is unzipped, loaded, and filtered by country and level.

In both cases the result is clipped against a population raster and saved to GeoPackage
format. We use GeoPackage since it is a single file rather than a directory (geodatabase)
or set of files (.shp).
"""

import tempfile
import warnings
import zipfile
from pathlib import Path

import geopandas as gpd
import zstandard
from tqdm import tqdm

from ..utils import clip_quietly, error, inform, update_local_provenance


class UnochaTransformer:
    def __init__(self) -> None:
        """Initialize the UNOCHA transformer.

        Returns:
            None
        """
        pass

    @staticmethod
    def description() -> str:
        """Return a brief description of this transformer.

        Returns:
            A string describing the transformation performed by this class.
        """
        return "Transform UNOCHA shape data to GeoPackage format, filtered by country and administrative level."

    def transform(
        self, shape_file: Path, iso_code: str, adm_level: int, raster_file: Path, output_dir: Path
    ) -> Path:
        """Transform UNOCHA administrative boundaries and combine with population data.

        Dispatches on the shape file type:

        - ``.gpkg.zstd``: decompresses the per-country, per-level GeoPackage from the
          laser-base UNOCHA repository and normalizes its columns.
        - ``.zip``: unzips the global geodatabase from UNOCHA's Humanitarian Data
          Exchange, loads it, and filters by country and administrative level.

        The resulting boundaries are then clipped against the population raster and
        saved as a GeoPackage file.

        Args:
            shape_file: Path to the UNOCHA shape data. Either a ``.gpkg.zstd`` file from
                the laser-base repository or a global ``.gdb.zip`` geodatabase.
            iso_code: ISO 3166-1 alpha-3 country code to filter for.
            adm_level: Administrative level to extract (0=country, 1=first-level, etc.).
            raster_file: Path to the WorldPop population raster file.
            output_dir: Directory where output GeoPackage will be saved.

        Returns:
            Path to the output GeoPackage file.

        Raises:
            ValueError: If shape_file is not a supported format (``.gpkg.zstd`` or
                ``.zip``), if no features are found for the specified country and
                administrative level, or if output_dir is not a directory.
        """

        inform(
            f"Starting UNOCHA transform with shape_file={shape_file}, iso_code={iso_code}, adm_level={adm_level}, raster_file={raster_file}, output_dir={output_dir}"
        )

        if shape_file.suffix == ".zstd":
            country_gdf, pcode = self._load_repository_data(shape_file, iso_code, adm_level)
        elif shape_file.suffix == ".zip":
            country_gdf, pcode = self._load_global_data(shape_file, iso_code, adm_level)
        else:
            error(
                f"Expected a .gpkg.zstd or .zip file for UNOCHA shape data, got: {shape_file}",
                ValueError,
            )

        # Ensure a sequential "nodeid" column shared by both formats.
        country_gdf["nodeid"] = list(range(len(country_gdf)))

        # using tempfile, create a temp directory, write the GeoDataFrame to a shapefile (.shp) in
        # that directory and use it with RasterToolkit to clip the raster file
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_shapefile = Path(tmpdir) / f"{iso_code}_admin{adm_level}.shp"
            country_gdf.to_file(tmp_shapefile, driver="ESRI Shapefile", engine="pyogrio")
            inform(f"Wrote temporary shapefile: {tmp_shapefile}")
            # Now we can use this temporary shapefile with RasterToolkit to clip the raster file
            pop_dict = clip_quietly(raster_file, tmp_shapefile, shape_attr=pcode)
            inform(f"Clipped raster with {tmp_shapefile}, got {len(pop_dict)} population values.")

            # Add a new column, population, to the GeoDataFrame, and fill it with the matching
            # values from the pop_dict dictionary. The keys of pop_dict should match the values in
            # the pcode column of the GeoDataFrame, and the values in pop_dict should be the
            # population values from the raster file.
            country_gdf["population"] = country_gdf[pcode].map(pop_dict)

        # Save the filtered GeoDataFrame to a GeoPackage file in the output directory
        if output_dir.is_dir():
            output_filename = output_dir / f"{iso_code}_admin{adm_level}.gpkg"
            country_gdf.to_file(output_filename, driver="GPKG")
            update_local_provenance(output_dir, output_filename, shape_file, raster_file)
            inform(f"Saved GeoPackage: {output_filename}")
        else:
            error(f"Output directory {output_dir} is not a directory.", ValueError)

        inform(f"UNOCHA transform complete: {output_filename}")
        return output_filename

    def _load_repository_data(
        self, shape_file: Path, iso_code: str, adm_level: int
    ) -> tuple[gpd.GeoDataFrame, str]:
        """Load and normalize per-country/level data from the laser-base repository.

        Decompresses the zstd-compressed GeoPackage, reads the single
        ``UNOCHA-<ISO>-ADM<level>`` layer (already scoped to one country and level),
        and trims and renames columns to the shared output schema.

        Args:
            shape_file: Path to the ``.gpkg.zstd`` file from the laser-base repository.
            iso_code: ISO 3166-1 alpha-3 country code, used for the layer name and a
                defensive filter.
            adm_level: Administrative level to extract.

        Returns:
            A tuple of the prepared GeoDataFrame (with a "name" column) and the name of
            the p-code column to use as the raster-clip shape attribute.

        Raises:
            ValueError: If no features are found for the country and level.
        """

        gpkg_file = self._decompress_zstd(shape_file)

        layer = f"UNOCHA-{iso_code.upper()}-ADM{adm_level}"
        inform(f"Loading UNOCHA repository data from {gpkg_file} layer {layer}...")
        gdf = gpd.read_file(gpkg_file, layer=layer)
        inform(f"Loaded GeoDataFrame for {layer} from {gpkg_file}, {len(gdf)} features.")

        # The repository file is already scoped to a single country, but filter
        # defensively in case the schema ever changes.
        if "iso3" in gdf.columns:
            gdf = gdf[gdf.iso3 == iso_code]
        if len(gdf) == 0:
            error(f"No features found for iso_code={iso_code} at admin{adm_level}.", ValueError)

        name_col = f"adm{adm_level}_name"
        pcode = f"adm{adm_level}_pcode"

        # Keep only the columns we use downstream; "dot_name" is retained for context.
        keep = [col for col in (name_col, "dot_name", pcode, "geometry") if col in gdf.columns]
        gdf = gdf[keep].copy()

        gdf["name"] = gdf[name_col]

        return gdf, pcode

    def _load_global_data(
        self, shape_file: Path, iso_code: str, adm_level: int
    ) -> tuple[gpd.GeoDataFrame, str]:
        """Load and filter data from the global UNOCHA/HDX geodatabase (fallback).

        Unzips the global geodatabase (if not already extracted), reads the
        ``admin<level>`` layer for all countries, filters by ISO code, and trims and
        renames columns to the shared output schema.

        Args:
            shape_file: Path to the global ``.gdb.zip`` geodatabase from HDX.
            iso_code: ISO 3166-1 alpha-3 country code to filter for.
            adm_level: Administrative level to extract.

        Returns:
            A tuple of the prepared GeoDataFrame (with a "name" column) and the name of
            the p-code column to use as the raster-clip shape attribute.

        Raises:
            ValueError: If the extracted geodatabase directory is missing or no
                features are found for the country and level.
        """

        # Determine the UNOCHA directory name from the shape file path
        # The directory name is the shape file path without the .zip extension
        source_dir = shape_file.parent
        # The extracted directory should contain a .gdb file with the same name as the directory
        # stem does _not_ include the suffix, so it will give us the directory name without the .zip extension
        gdb_dir = source_dir / shape_file.stem

        if not gdb_dir.exists():
            inform(f"Extracting {shape_file} to {source_dir}...")
            with zipfile.ZipFile(shape_file, "r") as zip_ref:
                members = zip_ref.infolist()
                for member in tqdm(members, desc="Extracting UNOCHA zip", unit="file"):
                    zip_ref.extract(member, path=source_dir)
            inform(f"Zip extraction complete: {gdb_dir}")

        if not gdb_dir.exists():
            error(
                f"Expected a .gdb file in the extracted UNOCHA directory, got: {gdb_dir}",
                ValueError,
            )

        gdf = read_gdb_quietly(gdb_dir, layer_name=f"admin{adm_level}")

        inform(f"Loaded GeoDataFrame for admin{adm_level} from {gdb_dir}, {len(gdf)} features.")

        # We should already have the admin level we want, now filter to the country level using the ISO code
        country_gdf = gdf[gdf.iso3 == iso_code]
        inform(f"Filtered GeoDataFrame for iso_code={iso_code}: {len(country_gdf)} features.")
        if len(country_gdf) == 0:
            error(f"No features found for iso_code={iso_code} at admin{adm_level}.", ValueError)

        # Filter the columns we will not be using
        names = [f"adm{i}_name" for i in range(adm_level + 1)]
        pcode = f"adm{adm_level}_pcode"
        country_gdf = country_gdf[names + [pcode, "geometry"]].copy()

        # Ensure a "name" column
        if adm_level < 4:
            country_gdf["name"] = country_gdf[f"adm{adm_level}_name"]
        else:
            country_gdf["name"] = country_gdf.adm3_name + country_gdf.adm4_name

        return country_gdf, pcode

    @staticmethod
    def _decompress_zstd(shape_file: Path) -> Path:
        """Decompress a zstd-compressed file alongside the source.

        Writes the decompressed file next to the source with the ``.zstd`` suffix
        removed (e.g. ``UNOCHA-SEN-ADM2.gpkg.zstd`` -> ``UNOCHA-SEN-ADM2.gpkg``). If the
        decompressed file already exists, it is reused.

        Args:
            shape_file: Path to the ``.gpkg.zstd`` file to decompress.

        Returns:
            Path to the decompressed GeoPackage file.
        """

        gpkg_file = shape_file.with_suffix("")

        if gpkg_file.exists():
            inform(f"Decompressed file already exists: {gpkg_file}.")
            return gpkg_file

        inform(f"Decompressing {shape_file} to {gpkg_file}...")
        decompressor = zstandard.ZstdDecompressor()
        with shape_file.open("rb") as compressed, gpkg_file.open("wb") as decompressed:
            decompressor.copy_stream(compressed, decompressed)
        inform(f"Decompression complete: {gpkg_file}")

        return gpkg_file


def read_gdb_quietly(gdb_path: Path, layer_name: str) -> gpd.GeoDataFrame:
    """Read a geodatabase layer while suppressing polygon processing warnings.

    Args:
        gdb_path: Path to the geodatabase directory.
        layer_name: Name of the layer to read from the geodatabase.

    Returns:
        GeoDataFrame containing the layer data.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"organizePolygons\(\) received a polygon with more than 100 parts.  The processing may be really slow.  You can skip the processing by setting METHOD=SKIP.",
            category=RuntimeWarning,
        )
        gdf = gpd.read_file(gdb_path, layer=layer_name)
    inform(f"Read GDB layer '{layer_name}' from {gdb_path}: {len(gdf)} features.")
    if len(gdf) == 0:
        inform(f"No features loaded from {gdb_path} layer '{layer_name}'.")

    return gdf
