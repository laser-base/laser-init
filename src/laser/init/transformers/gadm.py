"""
GADM shape data is available in various formats, including GeoPackage and Shapefile.
We will filter the data by country and administrative level, and ensure that it is in a consistent
format for loading into our database.
"""

import tempfile
from pathlib import Path

import geopandas as gpd

from ..utils import clip_quietly, error, inform, update_local_provenance


class GadmTransformer:
    def __init__(self) -> None:
        """Initialize the GADM transformer.

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
        return "Transform GADM shape data by filtering for country and administrative level."

    def transform(
        self, shape_file: Path, iso_code: str, adm_level: int, raster_file: Path, output_dir: Path
    ) -> Path:
        """Transform GADM administrative boundaries and combine with population data.

        Loads GADM shape data, filters by administrative level, clips population
        raster data to administrative boundaries, and saves as a GeoPackage file.

        Args:
            shape_file: Path to the GADM zip file containing shapefiles or gpkg file.
            iso_code: ISO 3166-1 alpha-3 country code.
            adm_level: Administrative level to extract (0=country, 1=regions, etc.).
            raster_file: Path to the WorldPop population raster file.
            output_dir: Directory where output GeoPackage will be saved.

        Returns:
            Path to the output GeoPackage file.

        Raises:
            NotImplementedError: If trying to use GeoPackage format (not yet supported).
            ValueError: If shape_file format is unsupported.
        """

        layer = f"gadm41_{iso_code.upper()}_{adm_level}"
        if shape_file.suffix == ".zip":
            inform(f"Processing GADM shape file from zip archive: {shape_file}")
        elif shape_file.suffix == ".gpkg":
            inform(f"Shape file is not a zip archive, proceeding with {shape_file}")
            raise NotImplementedError(
                "GADM GeoPackage format is not yet supported. Please provide a zip file containing the shapefile."
            )
        else:
            error(f"Unsupported shape file format: {shape_file.suffix}", ValueError)

        # geopandas/pyogrio reads the named shapefile layer directly from the zip archive.
        inform(f"Loading GADM data from {shape_file} layer {layer}...")
        gdf = gpd.read_file(shape_file, layer=layer)
        names = [f"NAME_{i}" for i in range(1, adm_level + 1)]
        gid = f"GID_{adm_level}"
        gdf = gdf[names + [gid, "geometry"]].copy()

        # Ensure "nodeid" and "name" columns
        gdf["nodeid"] = list(range(len(gdf)))
        if adm_level == 0:
            gdf["name"] = gdf.GID_0
        elif adm_level < 4:
            gdf["name"] = gdf[f"NAME_{adm_level}"]
        else:
            gdf["name"] = gdf.NAME_3.astype(str) + ":" + gdf.NAME_4.astype(str)

        # RasterToolkit needs a real shapefile path; the layer inside the zip is not a
        # usable filesystem path, so write the filtered frame to a temporary shapefile
        # and clip that (mirroring the UNOCHA transformer).
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_shapefile = Path(tmpdir) / f"{iso_code}_admin{adm_level}.shp"
            gdf.to_file(tmp_shapefile, driver="ESRI Shapefile", engine="pyogrio")
            inform(f"Wrote temporary shapefile: {tmp_shapefile}")
            pop_dict = clip_quietly(raster_file, tmp_shapefile, shape_attr=gid)
            gdf["population"] = gdf[gid].map(pop_dict)

        output_filename = output_dir / f"{iso_code}_admin{adm_level}.gpkg"
        gdf.to_file(output_filename, driver="GPKG")
        update_local_provenance(output_dir, output_filename, shape_file, raster_file)
        inform(f"Saved GeoPackage: {output_filename}")

        inform(f"GADM transform complete: {output_filename}")
        return output_filename
