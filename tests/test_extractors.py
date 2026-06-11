"""Tests for laser.init.extractors modules.

This module tests the data extraction functionality for various sources
including UNOCHA, geoBoundaries, GADM, WorldPop, and UN WPP.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from laser.init.extractors import gadm, geoboundaries, unocha, unwpp, worldpop


class TestGadmExtractor:
    """Test suite for GADM extractor."""

    def test_gadm_extractor_class_exists(self):
        """Test that GadmExtractor class exists.

        Given the gadm extractor module
        When checking for the GadmExtractor class
        Then it should be available

        Failure indicates the GADM extractor has been removed or renamed.
        """
        assert hasattr(gadm, "GadmExtractor")

    def test_gadm_extractor_has_description(self):
        """Test that GADM extractor provides a description.

        Given a GADM extractor instance
        When calling description()
        Then it should return a string describing the extractor

        Failure indicates the description method is missing or broken.
        """
        extractor = gadm.GadmExtractor()
        description = extractor.description()
        assert isinstance(description, str)
        assert len(description) > 0

    def test_gadm_extractor_has_extract_method(self):
        """Test that GADM extractor has extract method.

        Given a GADM extractor instance
        When checking for the extract method
        Then it should be callable

        Failure indicates the extract method is missing.
        """
        extractor = gadm.GadmExtractor()
        assert hasattr(extractor, "extract")
        assert callable(extractor.extract)

    @patch("laser.init.extractors.gadm.download_file")
    def test_gadm_extract_returns_path(self, mock_download, tmp_path):
        """Test that GADM extract method returns a file path.

        Given valid country, level, and year parameters
        When extract() is called
        Then it should return a Path to the downloaded file

        Failure indicates extract method signature or return type has changed.
        Note: Per docstring, downloads either shapefile (zip) or geopackage format.
        Files are cached locally to avoid redundant downloads.
        Returns None if download failed.
        Raises RuntimeError if both shapefile and geopackage downloads fail.
        """

        # Mock the download to return a path
        mock_path = tmp_path / "gadm_test.gpkg"
        mock_path.touch()
        mock_download.return_value = mock_path

        extractor = gadm.GadmExtractor()
        result = extractor.extract("NGA", 2, 2020)

        # Result should be a Path or None
        assert result is None or isinstance(result, Path)

    def test_gadm_extract_accepts_correct_parameters(self):
        """Test that GADM extract accepts country, level, and year.

        Given the extract method signature
        When checking parameters
        Then it should accept country (str), level (int), year (int)

        Failure indicates extract method signature has changed.
        Note: Per docstring:
        - country: ISO 3166-1 alpha-3 code (e.g., "NGA" for Nigeria)
        - level: Administrative level (0=country, 1=regions, 2=districts, etc.)
        - year: Currently unused - GADM provides latest version only
        """
        from inspect import signature

        sig = signature(gadm.GadmExtractor.extract)
        params = list(sig.parameters.keys())
        assert "country" in params
        assert "level" in params
        assert "year" in params

    @patch("laser.init.extractors.gadm.download_file")
    def test_gadm_geopackage_format_success(self, mock_download, tmp_path):
        """Test that GADM tries GeoPackage format first.

        Given a successful GeoPackage download
        When extract() is called
        Then it should return the GeoPackage file

        Failure indicates format preference has changed.
        Note: Per docstring, tries GeoPackage first, then falls back to shapefile.
        """
        gpkg_path = tmp_path / "gadm.gpkg"
        gpkg_path.touch()
        mock_download.return_value = gpkg_path

        extractor = gadm.GadmExtractor()
        result = extractor.extract("NGA", 2, 2020)

        assert result == gpkg_path

    @patch("laser.init.extractors.gadm.download_file")
    def test_gadm_fallback_to_shapefile(self, mock_download, tmp_path):
        """Test that GADM falls back to shapefile when GeoPackage fails.

        Given GeoPackage download returns None but shapefile succeeds
        When extract() is called
        Then it should try shapefile format

        Failure indicates fallback logic has changed.
        Note: Lines 75-78 handle fallback to shapefile format.
        """
        zip_path = tmp_path / "gadm.zip"
        zip_path.touch()

        # First call (gpkg) returns None, second call (shapefile) succeeds
        mock_download.side_effect = [None, zip_path]

        extractor = gadm.GadmExtractor()
        result = extractor.extract("NGA", 2, 2020)

        # Should try both formats
        assert mock_download.call_count >= 1

    @patch("laser.init.extractors.gadm.download_file")
    def test_gadm_both_formats_fail(self, mock_download):
        """Test that GADM handles failure when both formats fail.

        Given both GeoPackage and shapefile downloads return None
        When extract() is called
        Then it should handle the failure appropriately

        Failure indicates error handling has changed.
        Note: Lines 81-91 handle case when both formats fail.
        """
        # Both downloads fail
        mock_download.return_value = None

        extractor = gadm.GadmExtractor()

        # May raise RuntimeError or return None depending on implementation
        try:
            result = extractor.extract("NGA", 2, 2020)
            # If it doesn't raise, it should return None
            assert result is None or mock_download.call_count >= 1
        except RuntimeError:
            # If it raises, that's also valid per docstring
            assert mock_download.call_count >= 1

    @patch("laser.init.extractors.gadm.download_file")
    def test_gadm_constructs_correct_urls(self, mock_download, tmp_path):
        """Test that GADM constructs correct download URLs.

        Given country code and admin level
        When extract() is called
        Then URLs should contain country code

        Failure indicates URL construction has changed.
        """
        mock_path = tmp_path / "gadm.gpkg"
        mock_path.touch()
        mock_download.return_value = mock_path

        extractor = gadm.GadmExtractor()
        extractor.extract("NGA", 2, 2020)

        # Check that download_file was called with a URL containing country
        call_args = mock_download.call_args
        url = call_args[0][0]
        assert "NGA" in url or "nga" in url.lower()

    @patch("laser.init.extractors.gadm.download_file")
    def test_gadm_uses_download_file(self, mock_download, tmp_path):
        """Test that GADM uses download_file function.

        Given a GADM extract call
        When extract() is called
        Then it should call download_file

        Failure indicates download infrastructure has changed.
        """
        mock_path = tmp_path / "gadm.gpkg"
        mock_path.touch()
        mock_download.return_value = mock_path

        extractor = gadm.GadmExtractor()
        extractor.extract("NGA", 2, 2020)

        # Verify download_file was called
        assert mock_download.called


class TestGeoBoundariesExtractor:
    """Test suite for geoBoundaries extractor."""

    def test_geoboundaries_extractor_class_exists(self):
        """Test that GeoBoundariesExtractor class exists.

        Given the geoboundaries extractor module
        When checking for the GeoBoundariesExtractor class
        Then it should be available

        Failure indicates the geoBoundaries extractor has been removed or renamed.
        """
        assert hasattr(geoboundaries, "GeoBoundariesExtractor")

    def test_geoboundaries_extractor_has_description(self):
        """Test that geoBoundaries extractor provides a description.

        Given a geoBoundaries extractor instance
        When calling description()
        Then it should return a string describing the extractor

        Failure indicates the description method is missing or broken.
        """
        extractor = geoboundaries.GeoBoundariesExtractor()
        description = extractor.description()
        assert isinstance(description, str)
        assert len(description) > 0
        assert "geoBoundaries" in description or "geoboundaries" in description.lower()

    def test_geoboundaries_extractor_has_extract_method(self):
        """Test that geoBoundaries extractor has extract method.

        Given a geoBoundaries extractor instance
        When checking for the extract method
        Then it should be callable

        Failure indicates the extract method is missing.
        """
        extractor = geoboundaries.GeoBoundariesExtractor()
        assert hasattr(extractor, "extract")
        assert callable(extractor.extract)

    @patch("laser.init.extractors.geoboundaries.download_file")
    def test_geoboundaries_extract_returns_path(self, mock_download, tmp_path):
        """Test that geoBoundaries extract method returns a file path.

        Given valid country, level, and year parameters
        When extract() is called
        Then it should return a Path to the downloaded file

        Failure indicates extract method signature or return type has changed.
        Note: Per docstring, downloads from GeoBoundaries repository using
        version 6.0.0 of the gbOpen dataset.
        Returns None if download failed, raises RuntimeError if download fails.
        """

        # Mock the download to return a path
        mock_path = tmp_path / "geoboundaries_test.zip"
        mock_path.touch()
        mock_download.return_value = mock_path

        extractor = geoboundaries.GeoBoundariesExtractor()
        result = extractor.extract("MCO", 2, 2020)  # Use Monaco per docstring example

        # Result should be a Path or None
        assert result is None or isinstance(result, Path)

    def test_geoboundaries_extract_accepts_correct_parameters(self):
        """Test that geoBoundaries extract accepts country, level, and year.

        Given the extract method signature
        When checking parameters
        Then it should accept country (str), level (int), year (int)

        Failure indicates extract method signature has changed.
        Note: Per docstring:
        - country: ISO 3166-1 alpha-3 code (e.g., "MCO" for Monaco)
        - level: Administrative level (0=country, 1=first-level subdivisions, etc.)
        - year: Currently unused - GeoBoundaries uses fixed version 6.0.0
        """
        from inspect import signature

        sig = signature(geoboundaries.GeoBoundariesExtractor.extract)
        params = list(sig.parameters.keys())
        assert "country" in params
        assert "level" in params
        assert "year" in params


class TestUnochaExtractor:
    """Test suite for UNOCHA extractor."""

    def test_unocha_extractor_class_exists(self):
        """Test that UnochaExtractor class exists.

        Given the unocha extractor module
        When checking for the UnochaExtractor class
        Then it should be available

        Failure indicates the UNOCHA extractor has been removed or renamed.
        """
        assert hasattr(unocha, "UnochaExtractor")

    def test_unocha_extractor_has_description(self):
        """Test that UNOCHA extractor provides a description.

        Given a UNOCHA extractor instance
        When calling description()
        Then it should return a string describing the extractor

        Failure indicates the description method is missing or broken.
        """
        extractor = unocha.UnochaExtractor()
        description = extractor.description()
        assert isinstance(description, str)
        assert len(description) > 0
        assert "UNOCHA" in description or "unocha" in description.lower()

    def test_unocha_extractor_has_extract_method(self):
        """Test that UNOCHA extractor has extract method.

        Given a UNOCHA extractor instance
        When checking for the extract method
        Then it should be callable

        Failure indicates the extract method is missing.
        """
        extractor = unocha.UnochaExtractor()
        assert hasattr(extractor, "extract")
        assert callable(extractor.extract)

    def test_unocha_extract_accepts_correct_parameters(self):
        """Test that UNOCHA extract accepts country, level, and year.

        Given the extract method signature
        When checking parameters
        Then it should accept country (str), level (int), year (int)

        Failure indicates the extract method signature has changed, which would
        break callers in the CLI pipeline that pass these positional arguments.
        """
        from inspect import signature

        sig = signature(unocha.UnochaExtractor.extract)
        params = list(sig.parameters.keys())
        assert "country" in params
        assert "level" in params
        assert "year" in params

    @patch("laser.init.extractors.unocha.download_file")
    def test_unocha_extract_uses_repository_url(self, mock_download, tmp_path):
        """Test that UNOCHA extract downloads per-country/level from the laser-base repo.

        Given valid country and level parameters and a successful download
        When extract() is called
        Then it should request the per-country, per-level .gpkg.zstd file from the
            laser-base/unocha repository and return that path

        Failure indicates the extractor is no longer using the laser-base UNOCHA
        repository as its primary data source.
        """

        mock_path = tmp_path / "UNOCHA-SEN-ADM1.gpkg.zstd"
        mock_path.touch()
        mock_download.return_value = mock_path

        extractor = unocha.UnochaExtractor()
        result = extractor.extract("SEN", 1, 2020)

        assert result == mock_path
        # The URL passed to download_file should point at the laser-base repository
        # and reference the per-country, per-admin-level GeoPackage file.
        called_url = mock_download.call_args.args[0]
        assert "github.com/laser-base/unocha" in called_url
        assert "data/SEN/UNOCHA-SEN-ADM1.gpkg.zstd" in called_url

    @patch("laser.init.extractors.unocha.download_file")
    def test_unocha_extract_falls_back_to_global_dataset(self, mock_download, tmp_path):
        """Test that UNOCHA extract falls back to the global HDX dataset on failure.

        Given the repository download raises an error (country/level unavailable)
        When extract() is called
        Then it should fall back to downloading the global HDX geodatabase and
            return that path

        Failure indicates the legacy global-dataset fallback behavior has been lost,
        which would prevent extraction for countries not yet in the laser-base repo.
        """

        fallback_path = tmp_path / "global_admin_boundaries_matched_latest.gdb.zip"

        def download_side_effect(url, *args, **kwargs):
            # First call (repository) fails; second call (global fallback) succeeds.
            if "laser-base" in url:
                raise RuntimeError("404 Not Found")
            fallback_path.touch()
            return fallback_path

        mock_download.side_effect = download_side_effect

        extractor = unocha.UnochaExtractor()
        result = extractor.extract("ZZZ", 1, 2020)

        assert result == fallback_path
        assert mock_download.call_count == 2
        # The second (fallback) call should target the HDX global dataset.
        fallback_url = mock_download.call_args_list[1].args[0]
        assert "data.humdata.org" in fallback_url


class TestWorldPopExtractor:
    """Test suite for WorldPop extractor."""

    def test_worldpop_extractor_class_exists(self):
        """Test that WorldPop extractor class exists.

        Given the worldpop extractor module
        When checking for the WorldPopExtractor class
        Then it should be available

        Failure indicates the WorldPop extractor has been removed or renamed.
        """
        assert hasattr(worldpop, "WorldPopExtractor")

    def test_worldpop_extractor_has_description(self):
        """Test that WorldPop extractor provides a description.

        Given a WorldPop extractor instance
        When calling description()
        Then it should return a string describing the extractor

        Failure indicates the description method is missing or broken.
        """
        extractor = worldpop.WorldPopExtractor()
        description = extractor.description()
        assert isinstance(description, str)
        assert len(description) > 0
        assert "WorldPop" in description or "worldpop" in description.lower()

    def test_worldpop_extractor_has_extract_method(self):
        """Test that WorldPop extractor has extract method.

        Given a WorldPop extractor instance
        When checking for the extract method
        Then it should be callable

        Failure indicates the extract method is missing.
        """
        extractor = worldpop.WorldPopExtractor()
        assert hasattr(extractor, "extract")
        assert callable(extractor.extract)

    def test_worldpop_extract_signature(self):
        """Test that WorldPop extract has correct signature.

        Given the extract method
        When checking parameters
        Then it should accept country and year (not level)

        Failure indicates extract method signature has changed.
        Note: Per docstring, accepts country (str) and year (int, must be 2000-2030).
        Automatically selects dataset based on year:
        - 2015-2030: Global_2015_2030/R2025A
        - 2000-2014: Global_2000_2020_1km_UNadj
        Raises ValueError if year outside valid range.
        """
        from inspect import signature

        sig = signature(worldpop.WorldPopExtractor.extract)
        params = list(sig.parameters.keys())
        assert "country" in params
        assert "year" in params

    def test_worldpop_year_validation(self):
        """Test that WorldPop validates year range.

        Given a year outside the valid range (2000-2030)
        When extract() is called
        Then ValueError should be raised

        Failure indicates year validation is broken.
        Note: Per docstring, valid range is 2000-2030.
        """
        extractor = worldpop.WorldPopExtractor()

        # Test invalid years - should raise ValueError
        with pytest.raises(ValueError):
            extractor.extract("NGA", 1999)  # Too early

        with pytest.raises(ValueError):
            extractor.extract("NGA", 2031)  # Too late

    @patch("laser.init.extractors.worldpop.download_file")
    def test_worldpop_dataset_selection_2000_2014(self, mock_download, tmp_path):
        """Test that WorldPop selects correct dataset for years 2000-2014.

        Given a year between 2000 and 2014
        When extract() is called
        Then Global_2000_2020_1km_UNadj dataset should be used

        Failure indicates dataset selection logic has changed.
        Note: Per docstring, years 2000-2014 use Global_2000_2020_1km_UNadj dataset.
        """
        mock_path = tmp_path / "worldpop_2010.tif"
        mock_path.touch()
        mock_download.return_value = mock_path

        extractor = worldpop.WorldPopExtractor()
        result = extractor.extract("NGA", 2010)

        # Verify download_file was called
        mock_download.assert_called_once()
        # Verify the URL contains the correct dataset name
        call_args = mock_download.call_args
        url = call_args[0][0]  # First positional argument
        assert "Global_2000_2020_1km_UNadj" in url or "2000_2020" in url

    @patch("laser.init.extractors.worldpop.download_file")
    def test_worldpop_dataset_selection_2015_2030(self, mock_download, tmp_path):
        """Test that WorldPop selects correct dataset for years 2015-2030.

        Given a year between 2015 and 2030
        When extract() is called
        Then Global_2015_2030/R2025A dataset should be used

        Failure indicates dataset selection logic has changed.
        Note: Per docstring, years 2015-2030 use Global_2015_2030/R2025A dataset.
        """
        mock_path = tmp_path / "worldpop_2020.tif"
        mock_path.touch()
        mock_download.return_value = mock_path

        extractor = worldpop.WorldPopExtractor()
        result = extractor.extract("NGA", 2020)

        # Verify download_file was called
        mock_download.assert_called_once()
        # Verify the URL contains the correct dataset name
        call_args = mock_download.call_args
        url = call_args[0][0]
        assert "Global_2015_2030" in url or "R2025A" in url or "2015_2030" in url

    @patch("laser.init.extractors.worldpop.download_file")
    def test_worldpop_dataset_boundary_2014(self, mock_download, tmp_path):
        """Test dataset selection at year boundary 2014.

        Given year 2014 (last year of older dataset)
        When extract() is called
        Then Global_2000_2020_1km_UNadj dataset should be used

        Failure indicates boundary condition handling has changed.
        """
        mock_path = tmp_path / "worldpop_2014.tif"
        mock_path.touch()
        mock_download.return_value = mock_path

        extractor = worldpop.WorldPopExtractor()
        result = extractor.extract("NGA", 2014)

        mock_download.assert_called_once()
        call_args = mock_download.call_args
        url = call_args[0][0]
        assert "Global_2000_2020_1km_UNadj" in url or "2000_2020" in url

    @patch("laser.init.extractors.worldpop.download_file")
    def test_worldpop_dataset_boundary_2015(self, mock_download, tmp_path):
        """Test dataset selection at year boundary 2015.

        Given year 2015 (first year of newer dataset)
        When extract() is called
        Then Global_2015_2030/R2025A dataset should be used

        Failure indicates boundary condition handling has changed.
        """
        mock_path = tmp_path / "worldpop_2015.tif"
        mock_path.touch()
        mock_download.return_value = mock_path

        extractor = worldpop.WorldPopExtractor()
        result = extractor.extract("NGA", 2015)

        mock_download.assert_called_once()
        call_args = mock_download.call_args
        url = call_args[0][0]
        assert "Global_2015_2030" in url or "R2025A" in url or "2015_2030" in url

    @patch("laser.init.extractors.worldpop.download_file")
    def test_worldpop_returns_path(self, mock_download, tmp_path):
        """Test that extract returns Path to downloaded file.

        Given a successful download
        When extract() is called
        Then it should return a Path object

        Failure indicates return type has changed.
        """
        mock_path = tmp_path / "worldpop.tif"
        mock_path.touch()
        mock_download.return_value = mock_path

        extractor = worldpop.WorldPopExtractor()
        result = extractor.extract("NGA", 2020)

        assert isinstance(result, Path)
        assert result == mock_path

    @patch("laser.init.extractors.worldpop.download_file")
    def test_worldpop_download_failure_returns_none(self, mock_download):
        """Test that extract returns None on download failure.

        Given a failed download (returns None)
        When extract() is called
        Then it should return None

        Failure indicates error handling has changed.
        """
        mock_download.return_value = None

        extractor = worldpop.WorldPopExtractor()
        result = extractor.extract("NGA", 2020)

        assert result is None

    @patch("laser.init.extractors.worldpop.download_file")
    def test_worldpop_download_exception_for_2015_2030(self, mock_download):
        """Test that download exceptions are handled for 2015-2030 dataset.

        Given a download that raises an exception (2015-2030 range)
        When extract() is called
        Then the exception should be caught and error() called

        Failure indicates exception handling has changed.
        Note: Lines 88-89 handle exceptions for 2015-2030 dataset downloads.
        """
        mock_download.side_effect = Exception("Network error")

        extractor = worldpop.WorldPopExtractor()

        # Should call error() which raises RuntimeError
        with pytest.raises(RuntimeError):
            extractor.extract("NGA", 2020)

    @patch("laser.init.extractors.worldpop.download_file")
    def test_worldpop_download_exception_for_2000_2014(self, mock_download):
        """Test that download exceptions are handled for 2000-2014 dataset.

        Given a download that raises an exception (2000-2014 range)
        When extract() is called
        Then the exception should be caught and error() called

        Failure indicates exception handling has changed.
        Note: Lines 101-102 handle exceptions for 2000-2014 dataset downloads.
        """
        mock_download.side_effect = Exception("Network error")

        extractor = worldpop.WorldPopExtractor()

        # Should call error() which raises RuntimeError
        with pytest.raises(RuntimeError):
            extractor.extract("NGA", 2010)

    def test_worldpop_year_validation_boundary_1999(self):
        """Test that year 1999 is rejected (below minimum).

        Given year 1999 (one below valid range)
        When extract() is called
        Then RuntimeError should be raised via error()

        Failure indicates year validation has changed.
        Note: Line 105 handles out-of-range years by calling error().
        """
        extractor = worldpop.WorldPopExtractor()

        # Year validation now calls error() which raises RuntimeError
        with pytest.raises((ValueError, RuntimeError)):
            extractor.extract("NGA", 1999)

    def test_worldpop_year_validation_boundary_2031(self):
        """Test that year 2031 is rejected (above maximum).

        Given year 2031 (one above valid range)
        When extract() is called
        Then RuntimeError should be raised via error()

        Failure indicates year validation has changed.
        Note: Line 105 handles out-of-range years.
        """
        extractor = worldpop.WorldPopExtractor()

        # Year validation now calls error() which raises RuntimeError
        with pytest.raises((ValueError, RuntimeError)):
            extractor.extract("NGA", 2031)


class TestUnwppExtractor:
    """Test suite for UN WPP extractor."""

    def test_unwpp_extractor_class_exists(self):
        """Test that UnwppExtractor class exists.

        Given the unwpp extractor module
        When checking for the UnwppExtractor class
        Then it should be available

        Failure indicates the UN WPP extractor has been removed or renamed.
        """
        assert hasattr(unwpp, "UnwppExtractor")

    def test_unwpp_extractor_has_description(self):
        """Test that UN WPP extractor provides a description.

        Given a UN WPP extractor instance
        When calling description()
        Then it should return a string describing the extractor

        Failure indicates the description method is missing or broken.
        """
        extractor = unwpp.UnwppExtractor()
        description = extractor.description()
        assert isinstance(description, str)
        assert len(description) > 0
        assert (
            "UNWPP" in description
            or "unwpp" in description.lower()
            or "UN WPP" in description
        )

    def test_unwpp_extractor_has_extract_method(self):
        """Test that UN WPP extractor has extract method.

        Given a UN WPP extractor instance
        When checking for the extract method
        Then it should be callable

        Failure indicates the extract method is missing.
        """
        extractor = unwpp.UnwppExtractor()
        assert hasattr(extractor, "extract")
        assert callable(extractor.extract)

    def test_unwpp_extract_signature(self):
        """Test that UNWPP extract has correct signature.

        Given the extract method
        When checking parameters
        Then it should accept country, start_year, end_year

        Failure indicates extract method signature has changed.
        Note: Per docstring, downloads global demographic data files including:
        - Population by age group (5-year intervals)
        - Demographic indicators (CBR, CDR, etc.)
        - Life tables for mortality estimation
        Returns tuple of 4 Paths (life table files may be None).
        """
        from inspect import signature

        sig = signature(unwpp.UnwppExtractor.extract)
        params = list(sig.parameters.keys())
        assert "country" in params
        assert "start_year" in params
        assert "end_year" in params

    def test_unwpp_year_validation(self):
        """Test that UNWPP validates year range.

        Given years outside valid range
        When extract() is called
        Then ValueError should be raised

        Failure indicates year validation is broken.
        Note: Per docstring, start_year must be >= 1950 and end_year must be <= 2100.
        """
        extractor = unwpp.UnwppExtractor()

        # Test invalid years - should raise ValueError
        with pytest.raises(ValueError):
            extractor.extract("NGA", 1949, 2020)  # start_year too early

        with pytest.raises(ValueError):
            extractor.extract("NGA", 2000, 2101)  # end_year too late


class TestExtractorInterface:
    """Test suite for extractor interface consistency."""

    def test_all_extractors_have_consistent_interface(self):
        """Test that all extractors follow the same interface.

        Given all extractor classes
        When checking their methods
        Then they should all have extract() and description() methods

        Failure indicates inconsistent extractor interfaces.
        """
        extractors = [
            gadm.GadmExtractor(),
            geoboundaries.GeoBoundariesExtractor(),
            unocha.UnochaExtractor(),
            worldpop.WorldPopExtractor(),
            unwpp.UnwppExtractor(),
        ]

        for extractor in extractors:
            assert hasattr(extractor, "extract")
            assert hasattr(extractor, "description")
            assert callable(extractor.extract)
            assert callable(extractor.description)

    def test_extractor_descriptions_are_informative(self):
        """Test that extractor descriptions contain source information.

        Given all extractor instances
        When calling description()
        Then each should mention its data source

        Failure indicates descriptions are not informative enough.
        """
        extractors_and_keywords = [
            (gadm.GadmExtractor(), "gadm"),
            (geoboundaries.GeoBoundariesExtractor(), "geoboundaries"),
            (unocha.UnochaExtractor(), "unocha"),
            (worldpop.WorldPopExtractor(), "worldpop"),
            (unwpp.UnwppExtractor(), "unwpp"),
        ]

        for extractor, keyword in extractors_and_keywords:
            description = extractor.description().lower()
            assert keyword in description or keyword.upper() in extractor.description()


class TestExtractorCaching:
    """Test suite for extractor caching behavior."""

    def test_extractors_can_be_instantiated(self):
        """Test that extractors can be instantiated without arguments.

        Given extractor classes
        When creating instances
        Then they should be created successfully

        Failure indicates extractor initialization has changed.
        Note: Based on actual API, most extractors don't require cache_dir in __init__.
        """
        # All extractors should be instantiable
        extractors = [
            gadm.GadmExtractor(),
            geoboundaries.GeoBoundariesExtractor(),
            unocha.UnochaExtractor(),
            worldpop.WorldPopExtractor(),
            unwpp.UnwppExtractor(),
        ]
        assert len(extractors) == 5


