"""Tests for laser.init.transformers modules.

This module tests data transformation functionality that processes raw extracted
data into model-ready formats.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from laser.init.transformers import gadm, geoboundaries, unocha, unwpp


class TestTransformerInterfaces:
    """Test suite for transformer interface consistency."""

    def test_all_transformers_exist(self):
        """Test that all transformer classes exist.

        Given the transformers modules
        When checking for transformer classes
        Then GADM, geoBoundaries, UNOCHA, and UNWPP transformers should exist

        Failure indicates a transformer has been removed or renamed.
        """
        assert hasattr(gadm, "GadmTransformer")
        assert hasattr(geoboundaries, "GeoBoundariesTransformer")
        assert hasattr(unocha, "UnochaTransformer")
        assert hasattr(unwpp, "UnwppTransformer")

    def test_all_transformers_can_be_instantiated(self):
        """Test that all transformers can be instantiated.

        Given transformer classes
        When creating instances
        Then they should be created successfully

        Failure indicates transformer initialization has changed.
        """
        transformers = [
            gadm.GadmTransformer(),
            geoboundaries.GeoBoundariesTransformer(),
            unocha.UnochaTransformer(),
            unwpp.UnwppTransformer(),
        ]
        assert len(transformers) == 4

    def test_all_transformers_have_description(self):
        """Test that all transformers provide descriptions.

        Given transformer instances
        When calling description()
        Then each should return an informative string

        Failure indicates description method is missing or broken.
        """
        transformers = [
            gadm.GadmTransformer(),
            geoboundaries.GeoBoundariesTransformer(),
            unocha.UnochaTransformer(),
            unwpp.UnwppTransformer(),
        ]

        for transformer in transformers:
            assert hasattr(transformer, "description")
            assert callable(transformer.description)
            description = transformer.description()
            assert isinstance(description, str)
            assert len(description) > 0

    def test_all_transformers_have_transform(self):
        """Test that all transformers have transform method.

        Given transformer instances
        When checking for transform method
        Then it should be present and callable

        Failure indicates transform method is missing.
        """
        transformers = [
            gadm.GadmTransformer(),
            geoboundaries.GeoBoundariesTransformer(),
            unocha.UnochaTransformer(),
            unwpp.UnwppTransformer(),
        ]

        for transformer in transformers:
            assert hasattr(transformer, "transform")
            assert callable(transformer.transform)


class TestTransformerDescriptions:
    """Test suite for transformer descriptions."""

    def test_gadm_transformer_description(self):
        """Test GADM transformer description.

        Given a GADM transformer
        When calling description()
        Then it should mention GADM

        Failure indicates GADM description is unclear.
        """
        transformer = gadm.GadmTransformer()
        description = transformer.description()
        assert "gadm" in description.lower() or "GADM" in description

    def test_geoboundaries_transformer_description(self):
        """Test geoBoundaries transformer description.

        Given a geoBoundaries transformer
        When calling description()
        Then it should mention geoBoundaries

        Failure indicates geoBoundaries description is unclear.
        """
        transformer = geoboundaries.GeoBoundariesTransformer()
        description = transformer.description()
        assert "geoboundaries" in description.lower() or "geoBoundaries" in description

    def test_unocha_transformer_description(self):
        """Test UNOCHA transformer description.

        Given a UNOCHA transformer
        When calling description()
        Then it should mention UNOCHA

        Failure indicates UNOCHA description is unclear.
        """
        transformer = unocha.UnochaTransformer()
        description = transformer.description()
        assert "unocha" in description.lower() or "UNOCHA" in description

    def test_unwpp_transformer_description(self):
        """Test UN WPP transformer description.

        Given a UN WPP transformer
        When calling description()
        Then it should mention UN WPP or UNWPP

        Failure indicates UN WPP description is unclear.
        """
        transformer = unwpp.UnwppTransformer()
        description = transformer.description()
        assert "unwpp" in description.lower() or "UNWPP" in description or "UN WPP" in description


def _build_gadm_zip(tmp_path, iso, level, gids, names_by_level):
    """Build a GADM-style zip containing the shapefile layer gadm41_<ISO>_<level>.

    Mirrors the real GADM shapefile archive layout (a zip of .shp/.dbf/.shx/... parts)
    so transformer tests exercise the real zip-reading and clipping code paths rather
    than mocks.

    Args:
        tmp_path: pytest tmp_path directory to build in.
        iso: ISO-3 code used in the layer name and GID_0 column.
        level: Administrative level for the layer (e.g. 1).
        gids: List of GID_<level> values (one per feature).
        names_by_level: Mapping of level number to its NAME_<n> column values.

    Returns:
        Path to the created gadm41_<ISO>_shp.zip archive.
    """
    import zipfile

    import geopandas as gpd
    from shapely.geometry import Polygon

    n = len(gids)
    data = {"GID_0": [iso] * n}
    for lvl, values in names_by_level.items():
        data[f"NAME_{lvl}"] = values
    data[f"GID_{level}"] = gids
    geoms = [Polygon([(i, 0), (i + 1, 0), (i + 1, 1), (i, 1)]) for i in range(n)]
    gdf = gpd.GeoDataFrame({**data, "geometry": geoms}, crs="EPSG:4326")

    build_dir = tmp_path / "gadm_src"
    build_dir.mkdir(exist_ok=True)
    shp = build_dir / f"gadm41_{iso}_{level}.shp"
    gdf.to_file(shp, driver="ESRI Shapefile", engine="pyogrio")

    zip_path = tmp_path / f"gadm41_{iso}_shp.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for part in build_dir.glob(f"gadm41_{iso}_{level}.*"):
            zf.write(part, part.name)
    return zip_path


class TestGadmTransformer:
    """Test suite for GADM transformer functional tests."""

    def test_gadm_transform_signature(self):
        """Test that GADM transform has correct signature.

        Given the GADM transformer
        When checking transform method signature
        Then it should accept shape_file, iso_code, adm_level, raster_file, output_dir

        Failure indicates transform method signature has changed.
        Note: Per docstring:
        - shape_file: Path to GADM zip file containing shapefiles or gpkg file
        - iso_code: ISO 3166-1 alpha-3 country code
        - adm_level: Administrative level to extract (0=country, 1=regions, etc.)
        - raster_file: Path to WorldPop population raster file
        - output_dir: Directory where output GeoPackage will be saved
        Raises NotImplementedError if trying to use GeoPackage format (not yet supported).
        Raises ValueError if shape_file format is unsupported.
        """
        from inspect import signature

        sig = signature(gadm.GadmTransformer.transform)
        params = list(sig.parameters.keys())
        assert "shape_file" in params
        assert "iso_code" in params
        assert "adm_level" in params
        assert "raster_file" in params
        assert "output_dir" in params

    @patch("laser.init.transformers.gadm.update_local_provenance")
    @patch("laser.init.transformers.gadm.gpd.read_file")
    @patch("laser.init.transformers.gadm.clip_quietly")
    @patch("zipfile.ZipFile")
    def test_gadm_transform_returns_path(self, mock_zip, mock_clip, mock_read, mock_prov, tmp_path):
        """Test that GADM transform returns output file path.

        Given valid input files and parameters
        When transform() is called
        Then it should return a Path to the output GeoPackage

        Failure indicates transform return type has changed.
        Note: Per docstring, loads GADM shape data, filters by administrative level,
        clips population raster to boundaries, and saves as GeoPackage.
        """
        # Mock zipfile
        mock_zip_instance = MagicMock()
        mock_zip_instance.namelist.return_value = ["test.shp", "test.shx", "test.dbf"]
        mock_zip_instance.extractall = MagicMock()
        mock_zip.return_value.__enter__ = MagicMock(return_value=mock_zip_instance)
        mock_zip.return_value.__exit__ = MagicMock(return_value=False)

        # Mock geodataframe with required structure
        mock_gdf = MagicMock()
        mock_gdf.__len__ = MagicMock(return_value=2)
        mock_gdf.__iter__ = MagicMock(
            return_value=iter([{"geometry": MagicMock()}, {"geometry": MagicMock()}])
        )
        mock_gdf.to_file = MagicMock()
        mock_read.return_value = mock_gdf

        # Mock clip_quietly to return population data
        mock_clip.return_value = {"0": 1000.0, "1": 2000.0}

        # Mock provenance
        mock_prov.return_value = None

        transformer = gadm.GadmTransformer()
        shape_file = tmp_path / "test.zip"  # GADM uses .zip files
        shape_file.touch()
        raster_file = tmp_path / "test.tif"
        raster_file.touch()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = transformer.transform(shape_file, "NGA", 2, raster_file, output_dir)

        # Result should be a Path
        assert isinstance(result, Path)

    @patch("laser.init.transformers.gadm.update_local_provenance")
    @patch("laser.init.transformers.gadm.clip_quietly")
    def test_gadm_transform_reads_zip_and_clips_real_shapefile(
        self, mock_clip, mock_prov, tmp_path
    ):
        """Test that GADM transform reads the zipped shapefile and clips a real .shp.

        Given a real GADM-style zip archive with a single admin-level layer
        When transform() is called
        Then it reads the layer directly from the zip, hands clip_quietly an existing
            standalone shapefile (keyed by the GID column), and writes an output
            GeoPackage with name/nodeid/population columns

        Failure indicates a regression of the fix that replaced the invalid in-zip
        clip path with a temporary standalone shapefile. The raster clip itself is
        mocked (it is an external RasterToolkit call); everything else is real.
        """
        import geopandas as gpd

        zip_path = _build_gadm_zip(
            tmp_path,
            "TST",
            1,
            gids=["TST.1_1", "TST.2_1"],
            names_by_level={1: ["Region A", "Region B"]},
        )

        captured = {}

        def clip_side_effect(raster, shapefile, shape_attr):
            captured["exists"] = Path(shapefile).exists()
            captured["suffix"] = Path(shapefile).suffix
            captured["shape_attr"] = shape_attr
            return {"TST.1_1": 100.0, "TST.2_1": 200.0}

        mock_clip.side_effect = clip_side_effect
        mock_prov.return_value = None

        raster_file = tmp_path / "pop.tif"
        raster_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        result = gadm.GadmTransformer().transform(zip_path, "TST", 1, raster_file, output_dir)

        # The fix must hand clip_quietly a real, existing standalone .shp.
        assert captured["exists"], "clip_quietly must receive a shapefile that exists on disk"
        assert captured["suffix"] == ".shp"
        assert captured["shape_attr"] == "GID_1"

        assert result.exists()
        out = gpd.read_file(result)
        assert {"name", "nodeid", "population"} <= set(out.columns)
        assert set(out["population"]) == {100.0, 200.0}
        assert set(out["name"]) == {"Region A", "Region B"}

    @patch("laser.init.transformers.gadm.update_local_provenance")
    @patch("laser.init.transformers.gadm.clip_quietly")
    def test_gadm_transform_adm_level_0_uses_gid_0_as_name(self, mock_clip, mock_prov, tmp_path):
        """Test that GADM transform at admin level 0 derives name from GID_0.

        Given a level-0 GADM zip (country outline, GID_0 only)
        When transform() is called with adm_level=0
        Then the output "name" column is taken from GID_0

        Failure indicates the adm_level==0 naming branch has regressed.
        """
        import geopandas as gpd

        zip_path = _build_gadm_zip(tmp_path, "TST", 0, gids=["TST"], names_by_level={})
        mock_clip.return_value = {"TST": 5000.0}
        mock_prov.return_value = None

        raster_file = tmp_path / "pop.tif"
        raster_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        result = gadm.GadmTransformer().transform(zip_path, "TST", 0, raster_file, output_dir)

        out = gpd.read_file(result)
        assert list(out["name"]) == ["TST"]
        assert list(out["population"]) == [5000.0]

    @patch("laser.init.transformers.gadm.update_local_provenance")
    @patch("laser.init.transformers.gadm.clip_quietly")
    def test_gadm_transform_adm_level_4_concatenates_names(self, mock_clip, mock_prov, tmp_path):
        """Test that GADM transform at admin level 4 builds name from NAME_3:NAME_4.

        Given a level-4 GADM zip
        When transform() is called with adm_level=4
        Then the output "name" column is "<NAME_3>:<NAME_4>"

        Failure indicates the adm_level>=4 naming branch has regressed.
        """
        import geopandas as gpd

        zip_path = _build_gadm_zip(
            tmp_path,
            "TST",
            4,
            gids=["TST.1.1.1.1_1"],
            names_by_level={1: ["A"], 2: ["B"], 3: ["C"], 4: ["D"]},
        )
        mock_clip.return_value = {"TST.1.1.1.1_1": 42.0}
        mock_prov.return_value = None

        raster_file = tmp_path / "pop.tif"
        raster_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        result = gadm.GadmTransformer().transform(zip_path, "TST", 4, raster_file, output_dir)

        out = gpd.read_file(result)
        assert list(out["name"]) == ["C:D"]

    def test_gadm_transform_gpkg_raises_not_implemented(self, tmp_path):
        """Test that GADM transform rejects GeoPackage input.

        Given a .gpkg shape file
        When transform() is called
        Then NotImplementedError is raised (GeoPackage GADM input is not yet supported)

        Failure indicates the unsupported-format guard for .gpkg has changed.
        """
        shape_file = tmp_path / "gadm41_TST.gpkg"
        shape_file.touch()
        raster_file = tmp_path / "pop.tif"
        raster_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        with pytest.raises(NotImplementedError):
            gadm.GadmTransformer().transform(shape_file, "TST", 1, raster_file, output_dir)

    def test_gadm_transform_unsupported_format_raises_value_error(self, tmp_path):
        """Test that GADM transform rejects unsupported shape file formats.

        Given a shape file that is neither .zip nor .gpkg
        When transform() is called
        Then ValueError is raised

        Failure indicates the unsupported-format guard has changed.
        """
        shape_file = tmp_path / "boundaries.geojson"
        shape_file.touch()
        raster_file = tmp_path / "pop.tif"
        raster_file.touch()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        with pytest.raises(ValueError):
            gadm.GadmTransformer().transform(shape_file, "TST", 1, raster_file, output_dir)


class TestGeoBoundariesTransformer:
    """Test suite for geoBoundaries transformer functional tests."""

    def test_geoboundaries_transform_signature(self):
        """Test that geoBoundaries transform has correct signature.

        Given the geoBoundaries transformer
        When checking transform method signature
        Then it should accept shape_file, iso_code, adm_level, raster_file, output_dir

        Failure indicates transform method signature has changed.
        Note: Per docstring, loads GeoBoundaries shape data from zip file,
        extracts relevant attributes, clips population raster to boundaries,
        and saves as GeoPackage file.
        """
        from inspect import signature

        sig = signature(geoboundaries.GeoBoundariesTransformer.transform)
        params = list(sig.parameters.keys())
        assert "shape_file" in params
        assert "iso_code" in params
        assert "adm_level" in params
        assert "raster_file" in params
        assert "output_dir" in params

    @patch("laser.init.transformers.geoboundaries.update_local_provenance")
    @patch("laser.init.transformers.geoboundaries.gpd.read_file")
    @patch("laser.init.transformers.geoboundaries.clip_quietly")
    def test_geoboundaries_transform_returns_path(self, mock_clip, mock_read, mock_prov, tmp_path):
        """Test that geoBoundaries transform returns output file path.

        Given valid input files and parameters
        When transform() is called
        Then it should return a Path to the output GeoPackage

        Failure indicates transform return type has changed.
        """
        # Mock geodataframe with required structure
        mock_gdf = MagicMock()
        mock_gdf.__len__ = MagicMock(return_value=2)
        mock_gdf.__iter__ = MagicMock(
            return_value=iter([{"geometry": MagicMock()}, {"geometry": MagicMock()}])
        )
        mock_gdf.to_file = MagicMock()
        mock_read.return_value = mock_gdf

        # Mock clip_quietly to return population data
        mock_clip.return_value = {"0": 1000.0, "1": 2000.0}

        # Mock provenance tracking
        mock_prov.return_value = None

        transformer = geoboundaries.GeoBoundariesTransformer()
        shape_file = tmp_path / "test.shp"
        shape_file.touch()
        raster_file = tmp_path / "test.tif"
        raster_file.touch()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = transformer.transform(shape_file, "NGA", 2, raster_file, output_dir)

        # Result should be a Path
        assert isinstance(result, Path)


class TestUnochaTransformer:
    """Test suite for UNOCHA transformer functional tests."""

    def test_unocha_transform_signature(self):
        """Test that UNOCHA transform has correct signature.

        Given the UNOCHA transformer
        When checking transform method signature
        Then it should accept shape_file, iso_code, adm_level, raster_file, output_dir

        Failure indicates the transform method signature has changed, which would break
        the CLI pipeline that invokes it with these positional arguments.
        """
        from inspect import signature

        sig = signature(unocha.UnochaTransformer.transform)
        params = list(sig.parameters.keys())
        assert "shape_file" in params
        assert "iso_code" in params
        assert "adm_level" in params
        assert "raster_file" in params
        assert "output_dir" in params

    def test_unocha_transform_rejects_unsupported_format(self, tmp_path):
        """Test that UNOCHA transform rejects unsupported shape file formats.

        Given a shape file that is neither .gpkg.zstd nor .zip
        When transform() is called
        Then it should raise ValueError

        Failure indicates the transformer silently accepts formats it cannot process,
        which would later fail in a more confusing way downstream.
        """
        transformer = unocha.UnochaTransformer()
        shape_file = tmp_path / "boundaries.geojson"
        shape_file.touch()
        raster_file = tmp_path / "pop.tif"
        raster_file.touch()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(ValueError):
            transformer.transform(shape_file, "SEN", 1, raster_file, output_dir)

    @patch("laser.init.transformers.unocha.update_local_provenance")
    @patch("laser.init.transformers.unocha.clip_quietly")
    def test_unocha_transform_repository_gpkg_zstd(self, mock_clip, mock_prov, tmp_path):
        """Test that UNOCHA transform processes a laser-base repository .gpkg.zstd file.

        Given a zstd-compressed GeoPackage with the laser-base repository schema
            (iso3, adm{level}_name, adm{level}_pcode, dot_name, geometry)
        When transform() is called
        Then it should decompress the file, read the UNOCHA-<ISO>-ADM<level> layer,
            attach population, and return a Path to an output GeoPackage containing a
            "population" column

        Failure indicates the transformer can no longer consume the laser-base
        repository format that the updated extractor now downloads. This is an
        integration-style test that exercises real zstd decompression and GeoPackage
        I/O, mocking only the raster clip and provenance side effects.
        """
        import geopandas as gpd
        import zstandard
        from shapely.geometry import Polygon

        iso_code = "SEN"
        adm_level = 1
        pcode = f"adm{adm_level}_pcode"

        # Given: a repository-schema GeoDataFrame written to a .gpkg, then zstd-compressed.
        gdf = gpd.GeoDataFrame(
            {
                "iso3": [iso_code, iso_code],
                f"adm{adm_level}_name": ["Dakar", "Thies"],
                pcode: ["SN01", "SN02"],
                "dot_name": ["Senegal:Dakar", "Senegal:Thies"],
                "geometry": [
                    Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                    Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
                ],
            },
            crs="EPSG:4326",
        )
        gpkg_path = tmp_path / f"UNOCHA-{iso_code}-ADM{adm_level}.gpkg"
        layer = f"UNOCHA-{iso_code}-ADM{adm_level}"
        gdf.to_file(gpkg_path, layer=layer, driver="GPKG")

        zstd_path = tmp_path / f"UNOCHA-{iso_code}-ADM{adm_level}.gpkg.zstd"
        compressor = zstandard.ZstdCompressor()
        with gpkg_path.open("rb") as raw, zstd_path.open("wb") as compressed:
            compressor.copy_stream(raw, compressed)
        # Remove the intermediate .gpkg so the transformer must decompress it itself.
        gpkg_path.unlink()

        # The clip step is mocked: map each p-code to a synthetic population value.
        mock_clip.return_value = {"SN01": 1000.0, "SN02": 2000.0}
        mock_prov.return_value = None

        raster_file = tmp_path / "pop.tif"
        raster_file.touch()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        transformer = unocha.UnochaTransformer()

        # When: transform is invoked on the .gpkg.zstd file.
        result = transformer.transform(zstd_path, iso_code, adm_level, raster_file, output_dir)

        # Then: an output GeoPackage with a population column is produced.
        assert isinstance(result, Path)
        assert result.exists()
        result_gdf = gpd.read_file(result)
        assert "population" in result_gdf.columns
        assert "name" in result_gdf.columns
        assert "nodeid" in result_gdf.columns
        assert set(result_gdf["population"]) == {1000.0, 2000.0}
        # clip_quietly should have been called with the p-code as the shape attribute.
        assert mock_clip.call_args.kwargs["shape_attr"] == pcode

    @patch("laser.init.transformers.unocha.update_local_provenance")
    @patch("laser.init.transformers.unocha.clip_quietly")
    @patch("laser.init.transformers.unocha.read_gdb_quietly")
    def test_unocha_transform_global_zip_fallback(
        self, mock_read_gdb, mock_clip, mock_prov, tmp_path
    ):
        """Test that UNOCHA transform still handles the global .zip geodatabase fallback.

        Given a global geodatabase .zip whose extracted .gdb directory already exists
        When transform() is called
        Then it should read the admin<level> layer via read_gdb_quietly, filter by ISO
            code, attach population, and return a Path to an output GeoPackage

        Failure indicates the legacy global-dataset (HDX) code path has regressed, which
        would break extraction for countries served only by the fallback. The geodatabase
        read is mocked since a real .gdb cannot be created portably in a unit test.
        """
        import geopandas as gpd
        from shapely.geometry import Polygon

        iso_code = "SEN"
        adm_level = 1
        pcode = f"adm{adm_level}_pcode"

        # Given: a global-schema GeoDataFrame (multiple countries, hierarchical names).
        global_gdf = gpd.GeoDataFrame(
            {
                "iso3": [iso_code, iso_code, "MLI"],
                "adm0_name": ["Senegal", "Senegal", "Mali"],
                "adm1_name": ["Dakar", "Thies", "Bamako"],
                pcode: ["SN01", "SN02", "ML01"],
                "geometry": [
                    Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                    Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
                    Polygon([(2, 0), (3, 0), (3, 1), (2, 1)]),
                ],
            },
            crs="EPSG:4326",
        )
        mock_read_gdb.return_value = global_gdf

        # The extracted .gdb directory must exist so the transformer skips unzipping.
        shape_file = tmp_path / "global_admin_boundaries_matched_latest.gdb.zip"
        shape_file.touch()
        gdb_dir = tmp_path / shape_file.stem  # "global_admin_boundaries_matched_latest.gdb"
        gdb_dir.mkdir()

        mock_clip.return_value = {"SN01": 500.0, "SN02": 750.0}
        mock_prov.return_value = None

        raster_file = tmp_path / "pop.tif"
        raster_file.touch()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        transformer = unocha.UnochaTransformer()

        # When: transform is invoked on the global .zip file.
        result = transformer.transform(shape_file, iso_code, adm_level, raster_file, output_dir)

        # Then: the global geodatabase reader was used and a filtered output produced.
        mock_read_gdb.assert_called_once()
        assert isinstance(result, Path)
        assert result.exists()
        result_gdf = gpd.read_file(result)
        # Only the two SEN features should survive the ISO filter.
        assert len(result_gdf) == 2
        assert "population" in result_gdf.columns
        assert set(result_gdf["population"]) == {500.0, 750.0}


class TestUnwppTransformer:
    """Test suite for UNWPP transformer functional tests."""

    def test_unwpp_transform_signature(self):
        """Test that UNWPP transform has correct signature.

        Given the UNWPP transformer
        When checking transform method signature
        Then it should accept stats_data, iso_code, start_year, end_year, output_dir

        Failure indicates transform method signature has changed.
        Note: Per docstring, produces three output CSV files:
        - CBR/CDR (crude birth/death rates) by year
        - Age distribution (population by 5-year age groups) at start_year
        - Life expectancy (cumulative deaths for survival) at start_year
        """
        from inspect import signature

        sig = signature(unwpp.UnwppTransformer.transform)
        params = list(sig.parameters.keys())
        assert "stats_data" in params
        assert "iso_code" in params
        assert "start_year" in params
        assert "end_year" in params
        assert "output_dir" in params

    def test_unwpp_transform_returns_tuple_of_paths_signature_only(self):
        """Test that UNWPP transform has correct return type signature.

        Given the UNWPP transform method
        When checking return type annotation
        Then it should return a tuple of Paths

        Failure indicates return type signature has changed.
        Note: Per docstring, returns tuple of 3 Path objects for the output CSV files:
        - cxr.csv: CBR/CDR by year
        - age_dist.csv: Age distribution at start_year
        - life_exp.csv: Life expectancy at start_year

        Full functional testing requires complex provenance setup with proper
        cache directory structure, so we validate the signature here.
        """
        from inspect import signature

        sig = signature(unwpp.UnwppTransformer.transform)

        # Check that return annotation indicates tuple
        return_annotation = sig.return_annotation
        # Should return tuple of Paths per docstring
        assert "tuple" in str(return_annotation).lower() or "Tuple" in str(return_annotation)
