"""Tests for laser.init.generate module (laser-generate entry point).

Covers module/entry-point existence, argument parsing, data-building helpers,
and file writers. All tests are offline — network calls are mocked.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
import pytest

from laser.init import generate as gen

# ── Sample data shared across tests ───────────────────────────────────────────

SAMPLE_FC = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"nodeid": 0, "name": "North"},
            "geometry": {"type": "Polygon", "coordinates": [
                [[3.0, 7.0], [3.0, 14.0], [15.0, 14.0], [15.0, 7.0], [3.0, 7.0]]
            ]},
        },
        {
            "type": "Feature",
            "properties": {"nodeid": 1, "name": "South"},
            "geometry": {"type": "Polygon", "coordinates": [
                [[3.0, 4.0], [3.0, 7.0], [15.0, 7.0], [15.0, 4.0], [3.0, 4.0]]
            ]},
        },
    ],
}

SAMPLE_POP = {"0": 100_000.0, "1": 50_000.0}

SAMPLE_DEMO = {
    "cxr": [{"year": 2020, "CBR": 37.0, "CDR": 13.0}],
    "age_dist": [
        {"age_start": 0, "pop_total": 20000},
        {"age_start": 5, "pop_total": 18000},
    ],
    "life_exp": [{"cumulative_deaths": i * 100} for i in range(101)],
}


# ── Entry point existence ──────────────────────────────────────────────────────

class TestEntryPoint:
    def test_main_callable(self):
        """main() must exist and be callable — it is the laser-generate entry point."""
        assert callable(gen.main)

    def test_entry_point_registered(self):
        """laser-generate must be declared in pyproject.toml [project.scripts]."""
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert 'laser-generate = "laser.init.generate:main"' in content

    def test_module_importable(self):
        """laser.init.generate must be importable (i.e. it lives in the package tree)."""
        import laser.init.generate  # noqa: F401


# ── Argument parsing ───────────────────────────────────────────────────────────

class TestArgParsing:
    def _parse(self, argv):
        """Run main() with mocked HTTP and sys.argv; return exit code."""
        with patch.object(sys, "argv", ["laser-generate"] + argv):
            with patch.object(gen, "fetch_shapes", return_value=SAMPLE_FC):
                with patch.object(gen, "fetch_population", return_value=SAMPLE_POP):
                    with patch.object(gen, "fetch_demographics", return_value=SAMPLE_DEMO):
                        try:
                            gen.main()
                            return 0
                        except SystemExit as exc:
                            return exc.code

    def test_help_exits_zero(self):
        """--help must print usage and exit 0."""
        with patch.object(sys, "argv", ["laser-generate", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                gen.main()
        assert exc_info.value.code == 0

    def test_missing_args_exits_nonzero(self):
        """Omitting required positional args must exit non-zero."""
        with patch.object(sys, "argv", ["laser-generate"]):
            with pytest.raises(SystemExit) as exc_info:
                gen.main()
        assert exc_info.value.code != 0

    def test_default_shape_source_is_unocha(self, tmp_path):
        """--shape-source defaults to 'unocha' when not specified.

        Patches _default_shapes_url to return a known sentinel per source, so
        the assertion is independent of any laser_config.yaml on the dev's box.
        """
        called_urls = []

        def capture_shapes(url, iso, level):
            called_urls.append(url)
            return SAMPLE_FC

        def fake_default(source):
            return f"http://test-{source}.example"

        with patch.object(sys, "argv", ["laser-generate", "NGA", "1", "2020", "2020",
                                         "--output-dir", str(tmp_path)]):
            with patch.object(gen, "_default_shapes_url", side_effect=fake_default):
                with patch.object(gen, "fetch_shapes", side_effect=capture_shapes):
                    with patch.object(gen, "fetch_population", return_value=SAMPLE_POP):
                        with patch.object(gen, "fetch_demographics", return_value=SAMPLE_DEMO):
                            gen.main()

        assert len(called_urls) == 1
        assert "test-unocha" in called_urls[0]

    def test_gadm_shape_source_uses_correct_port(self, tmp_path):
        """--shape-source gadm must route to the gadm URL, not unocha's."""
        called_urls = []

        def capture_shapes(url, iso, level):
            called_urls.append(url)
            return SAMPLE_FC

        def fake_default(source):
            return f"http://test-{source}.example"

        with patch.object(sys, "argv", ["laser-generate", "NGA", "1", "2020", "2020",
                                         "--shape-source", "gadm",
                                         "--output-dir", str(tmp_path)]):
            with patch.object(gen, "_default_shapes_url", side_effect=fake_default):
                with patch.object(gen, "fetch_shapes", side_effect=capture_shapes):
                    with patch.object(gen, "fetch_population", return_value=SAMPLE_POP):
                        with patch.object(gen, "fetch_demographics", return_value=SAMPLE_DEMO):
                            gen.main()

        assert "test-gadm" in called_urls[0]


# ── Data-building helpers ──────────────────────────────────────────────────────

class TestBuildGdf:
    def test_returns_geodataframe(self):
        """build_gdf must return a GeoDataFrame."""
        gdf = gen.build_gdf(SAMPLE_FC, SAMPLE_POP)
        assert isinstance(gdf, gpd.GeoDataFrame)

    def test_row_count_matches_features(self):
        """One row per feature."""
        gdf = gen.build_gdf(SAMPLE_FC, SAMPLE_POP)
        assert len(gdf) == len(SAMPLE_FC["features"])

    def test_population_values_correct(self):
        """Population column must reflect the pop dict values, rounded."""
        gdf = gen.build_gdf(SAMPLE_FC, SAMPLE_POP)
        assert gdf.loc[gdf.nodeid == 0, "population"].iloc[0] == 100_000
        assert gdf.loc[gdf.nodeid == 1, "population"].iloc[0] == 50_000

    def test_sorted_by_nodeid(self):
        """Rows must be sorted by nodeid ascending."""
        gdf = gen.build_gdf(SAMPLE_FC, SAMPLE_POP)
        assert list(gdf.nodeid) == sorted(gdf.nodeid.tolist())

    def test_crs_is_wgs84(self):
        """GeoDataFrame must have WGS-84 CRS."""
        gdf = gen.build_gdf(SAMPLE_FC, SAMPLE_POP)
        assert gdf.crs is not None
        assert gdf.crs.to_epsg() == 4326

    def test_missing_pop_defaults_to_zero(self):
        """Features absent from pop dict get population=0."""
        gdf = gen.build_gdf(SAMPLE_FC, {"0": 999.0})  # nodeid 1 missing
        assert gdf.loc[gdf.nodeid == 1, "population"].iloc[0] == 0


# ── File writers ───────────────────────────────────────────────────────────────

class TestFileWriters:
    @pytest.fixture
    def gdf(self):
        return gen.build_gdf(SAMPLE_FC, SAMPLE_POP)

    def test_write_gpkg_creates_file(self, tmp_path, gdf):
        dest = gen.write_gpkg(gdf, tmp_path, "NGA", 1)
        assert dest.exists()
        assert dest.name == "NGA_admin1.gpkg"

    def test_write_gpkg_readable(self, tmp_path, gdf):
        dest = gen.write_gpkg(gdf, tmp_path, "NGA", 1)
        result = gpd.read_file(dest)
        assert len(result) == len(gdf)

    def test_write_cxr_creates_file(self, tmp_path):
        dest = gen.write_cxr(SAMPLE_DEMO, tmp_path)
        assert dest.exists()
        df = pd.read_csv(dest)
        assert list(df.columns) == ["Time", "CBR", "CDR"]
        assert len(df) == 1
        assert df.iloc[0]["CBR"] == pytest.approx(37.0)

    def test_write_age_dist_creates_file(self, tmp_path):
        dest = gen.write_age_dist(SAMPLE_DEMO, tmp_path)
        assert dest.exists()
        df = pd.read_csv(dest)
        assert list(df.columns) == ["AgeGrpStart", "PopTotal"]
        assert len(df) == 2

    def test_write_life_exp_creates_file(self, tmp_path):
        dest = gen.write_life_exp(SAMPLE_DEMO, tmp_path)
        assert dest.exists()
        df = pd.read_csv(dest)
        assert "cumulative_deaths" in df.columns
        assert len(df) == 101

    def test_write_provenance_creates_json(self, tmp_path):
        dest = gen.write_provenance(
            tmp_path, "NGA", 1,
            "http://localhost:8101", "http://localhost:8104", "http://localhost:8100",
            "gadm", 2020,
        )
        assert dest.exists()
        prov = json.loads(dest.read_text())
        assert "NGA_admin1.gpkg" in prov
        assert prov["NGA_admin1.gpkg"]["worldpop_year"] == 2020


# ── End-to-end (offline, mocked services) ─────────────────────────────────────

class TestMainEndToEnd:
    def test_produces_expected_files(self, tmp_path):
        """Running main() with mocked services must produce all core output files."""
        with patch.object(sys, "argv", ["laser-generate", "NGA", "1", "2020", "2020",
                                         "--output-dir", str(tmp_path)]):
            with patch.object(gen, "fetch_shapes", return_value=SAMPLE_FC):
                with patch.object(gen, "fetch_population", return_value=SAMPLE_POP):
                    with patch.object(gen, "fetch_demographics", return_value=SAMPLE_DEMO):
                        gen.main()

        assert (tmp_path / "NGA_admin1.gpkg").exists()
        assert (tmp_path / "cxr.csv").exists()
        assert (tmp_path / "age_dist.csv").exists()
        assert (tmp_path / "life_exp.csv").exists()
        assert (tmp_path / "provenance.json").exists()
        assert (tmp_path / "config.yaml").exists()

    def test_raster_year_clamped_to_2020(self, tmp_path):
        """start_year > 2020 must clamp raster_year to 2020 (WorldPop cap)."""
        pop_years = []

        def capture_pop(url, iso, year, fc):
            pop_years.append(year)
            return SAMPLE_POP

        with patch.object(sys, "argv", ["laser-generate", "NGA", "1", "2025", "2025",
                                         "--output-dir", str(tmp_path)]):
            with patch.object(gen, "fetch_shapes", return_value=SAMPLE_FC):
                with patch.object(gen, "fetch_population", side_effect=capture_pop):
                    with patch.object(gen, "fetch_demographics", return_value=SAMPLE_DEMO):
                        gen.main()

        assert pop_years == [2020]
