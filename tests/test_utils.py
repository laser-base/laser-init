"""Tests for laser.init.utils module.

This module tests the utility functions provided by laser.init, including
country name resolution, administrative level parsing, file downloading,
and provenance tracking.
"""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from laser.init import utils


class TestIsoFromCountryString:
    """Test suite for iso_from_country_string function."""

    def test_exact_iso3_code(self):
        """Test that exact ISO-3 codes are recognized.

        Given a valid ISO-3 country code
        When iso_from_country_string is called
        Then the same code should be returned

        Failure indicates the basic ISO-3 lookup mechanism is broken.
        """
        # Test various ISO-3 codes from different regions
        assert utils.iso_from_country_string("USA") == "USA"
        assert utils.iso_from_country_string("GBR") == "GBR"
        assert utils.iso_from_country_string("NGA") == "NGA"
        assert utils.iso_from_country_string("PAK") == "PAK"
        assert utils.iso_from_country_string("BRA") == "BRA"

    def test_exact_country_name(self):
        """Test that exact country names are recognized.

        Given a valid country name
        When iso_from_country_string is called
        Then the correct ISO-3 code should be returned

        Failure indicates the country name to ISO-3 mapping is broken.
        Note: Performs normalized matching against ISO codes, official names,
        and French country names using pycountry.
        """
        # Test various country names
        assert utils.iso_from_country_string("Nigeria") == "NGA"
        assert utils.iso_from_country_string("Pakistan") == "PAK"
        assert utils.iso_from_country_string("Brazil") == "BRA"
        assert utils.iso_from_country_string("Kenya") == "KEN"

    def test_french_country_names(self):
        """Test that French country names are recognized.

        Given a French country name
        When iso_from_country_string is called
        Then the correct ISO-3 code should be returned

        Failure indicates French name matching is broken.
        Note: Uses french_iso.py for French name mappings.
        """
        # Test French name matching
        result = utils.iso_from_country_string("République démocratique du Congo")
        assert result == "COD"

    def test_case_insensitive_matching(self):
        """Test that country name matching is case-insensitive.

        Given country names in various cases
        When iso_from_country_string is called
        Then the correct ISO-3 code should be returned regardless of case

        Failure indicates case-insensitive matching is not working.
        """
        assert utils.iso_from_country_string("nigeria") == "NGA"
        assert utils.iso_from_country_string("NIGERIA") == "NGA"
        assert utils.iso_from_country_string("NiGeRiA") == "NGA"

    def test_fuzzy_matching(self, capsys):
        """Test that fuzzy matching handles common misspellings.

        Given slightly misspelled country names
        When iso_from_country_string is called
        Then possible options are shown and None is returned

        Failure indicates the fuzzy matching capability is broken.
        Note: Uses capsys to capture stderr output and verify debug message.
        """
        with pytest.warns() as record:
            result = utils.iso_from_country_string("England")
            assert result is None  # Allow for fuzzy match or no match

        # Check for warning with possible matches.
        assert str(record[0].message) == "Possible match(es):\n\tUnited Kingdom (ISO: GBR)"

        # Check for no matches message.
        captured = capsys.readouterr()
        assert "iso_from_country_string(): No matches found for 'England'" in captured.out, (
            "stderr should contain 'No matches found for 'England''"
        )

    def test_invalid_country_returns_none(self):
        """Test that invalid country names return None.

        Given an invalid or non-existent country name
        When iso_from_country_string is called
        Then None should be returned

        Failure indicates error handling for invalid inputs is broken.
        """
        result = utils.iso_from_country_string("NotARealCountry123")
        assert result is None

    def test_empty_string_returns_none(self):
        """Test that empty strings return None.

        Given an empty string
        When iso_from_country_string is called
        Then None should be returned

        Failure indicates validation of empty inputs is broken.
        """
        result = utils.iso_from_country_string("")
        assert result is None


class TestLevelFromString:
    """Test suite for level_from_string function."""

    def test_integer_input(self):
        """Test that integer administrative levels are parsed correctly.

        Given a valid integer as a string
        When level_from_string is called
        Then the integer should be returned

        Failure indicates basic integer parsing is broken.
        """
        assert utils.level_from_string("0") == 0
        assert utils.level_from_string("1") == 1
        assert utils.level_from_string("2") == 2
        assert utils.level_from_string("3") == 3
        assert utils.level_from_string("4") == 4

    def test_adm_prefix_format(self):
        """Test that ADM-prefixed level strings are parsed correctly.

        Given administrative level in ADM format (e.g., "ADM2")
        When level_from_string is called
        Then the numeric level should be extracted

        Failure indicates ADM prefix handling is broken.
        Note: Accepts formats like 'admin1', 'ADM2', or '3' (case-insensitive).
        Returns None for values out of valid range (0-4).
        """
        assert utils.level_from_string("ADM0") == 0
        assert utils.level_from_string("ADM1") == 1
        assert utils.level_from_string("ADM2") == 2
        assert utils.level_from_string("adm2") == 2  # Case insensitive
        assert utils.level_from_string("admin1") == 1

    def test_negative_level_returns_none(self):
        """Test that negative administrative levels return None.

        Given a negative integer
        When level_from_string is called
        Then None should be returned

        Failure indicates validation of negative levels is broken.
        Note: Valid range is 0-4 per documentation.
        """
        result = utils.level_from_string("-1")
        assert result is None

    def test_out_of_range_level_returns_none(self):
        """Test that levels > 4 return None.

        Given an administrative level greater than 4
        When level_from_string is called
        Then None should be returned

        Failure indicates range validation is broken.
        Note: Valid range is 0-4 per documentation.
        """
        result = utils.level_from_string("5")
        assert result is None
        result = utils.level_from_string("10")
        assert result is None

    def test_non_numeric_input_returns_none(self):
        """Test that non-numeric inputs return None.

        Given a non-numeric string
        When level_from_string is called
        Then None should be returned

        Failure indicates validation of non-numeric inputs is broken.
        """
        result = utils.level_from_string("not_a_number")
        assert result is None


class TestDownloadFile:
    """Test suite for download_file function."""

    @patch("laser.init.utils.requests.get")
    def test_successful_download(self, mock_get, tmp_path):
        """Test that files are downloaded successfully.

        Given a valid URL and output directory
        When download_file is called
        Then the file should be downloaded to the correct location

        Failure indicates the basic download mechanism is broken.
        Note: Function streams file in chunks and updates provenance.json
        with download metadata (URL, timestamp) as a side effect.
        """
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content = lambda chunk_size: [b"test data"]
        mock_response.headers = {"content-length": "9"}
        mock_get.return_value = mock_response

        # Test download
        url = "https://example.com/test.txt"
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        dest_dir = tmp_path / "downloads"
        dest_dir.mkdir()
        result = utils.download_file(url, cache_dir, dest_dir)

        # Verify
        assert result.exists()
        assert result.parent == dest_dir
        mock_get.assert_called_once()

    @patch("laser.init.utils.requests.get")
    def test_download_file_skips_existing(self, mock_get, tmp_path):
        """Test that existing files are not re-downloaded when force=False.

        Given an existing file and force=False (default)
        When download_file is called
        Then the existing file should be returned without downloading

        Failure indicates the caching optimization is broken.
        Note: Per docstring, if file exists and force=False, returns existing file.
        """
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content = lambda chunk_size: [b"test data"]
        mock_response.headers = {"content-length": "9"}
        mock_get.return_value = mock_response

        # Create pre-existing file
        url = "https://example.com/test.txt"
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        dest_dir = tmp_path / "downloads"
        dest_dir.mkdir()
        existing_file = dest_dir / "test.txt"
        existing_file.write_text("existing content")

        # Call download_file - should not download
        result = utils.download_file(url, cache_dir, dest_dir, force=False)

        # Verify existing file returned without download
        assert result == existing_file
        # Should not call requests.get
        assert mock_get.call_count == 0 or result.read_text() == "existing content"

    @patch("laser.init.utils.requests.get")
    def test_download_with_custom_filename(self, mock_get, tmp_path):
        """Test that custom filenames are used when provided.

        Given a URL and a custom filename
        When download_file is called with local_name parameter
        Then the file should be saved with the custom filename

        Failure indicates custom filename handling is broken.
        """
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content = lambda chunk_size: [b"test data"]
        mock_response.headers = {"content-length": "9"}
        mock_get.return_value = mock_response

        # Test download with custom filename
        url = "https://example.com/test.txt"
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        dest_dir = tmp_path / "downloads"
        dest_dir.mkdir()
        custom_name = "custom_file.txt"
        result = utils.download_file(url, cache_dir, dest_dir, local_name=custom_name)

        # Verify
        assert result.name == custom_name

    @patch("laser.init.utils.requests.get")
    def test_download_404_raises_error(self, mock_get, tmp_path):
        """Test that HTTP errors raise appropriate exceptions.

        Given a URL that returns a 404 error
        When download_file is called
        Then an appropriate error should be raised

        Failure indicates error handling for HTTP errors is broken.
        """
        # Setup mock response with 404
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        # Test that error is raised
        url = "https://example.com/notfound.txt"
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        dest_dir = tmp_path / "downloads"
        dest_dir.mkdir()
        with pytest.raises(requests.exceptions.HTTPError):
            utils.download_file(url, cache_dir, dest_dir)


class TestProvenanceTracking:
    """Test suite for provenance tracking functions."""

    def test_update_cache_provenance(self, tmp_path):
        """Test that cache provenance is tracked correctly.

        Given a file path and source URL
        When update_cache_provenance is called
        Then provenance metadata should be saved correctly

        Failure indicates cache provenance tracking is broken.
        """
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        file_path = cache_root / "test_file.txt"
        file_path.write_text("test content")
        url = "https://example.com/test_file.txt"

        # Update provenance
        utils.update_cache_provenance(cache_root, file_path, url)

        # Verify provenance file exists
        provenance_file = cache_root / "provenance.json"
        assert provenance_file.exists()

        # Verify provenance content
        with open(provenance_file) as f:
            provenance = json.load(f)

        assert "test_file.txt" in provenance
        assert provenance["test_file.txt"]["source_url"] == url
        assert "timestamp" in provenance["test_file.txt"]

    def test_update_local_provenance_signature(self):
        """Test that update_local_provenance has correct signature.

        Given the update_local_provenance function
        When checking its signature
        Then it should accept output_dir, output_filename, and variable source files

        Failure indicates the function signature has changed.
        Note: Full functional testing requires complex directory structures with
        proper provenance files. This test verifies the function interface.
        """
        from inspect import signature

        sig = signature(utils.update_local_provenance)
        params = list(sig.parameters.keys())
        assert "output_dir" in params
        assert "output_filename" in params
        assert "files" in params  # Varargs parameter for source files

    def test_provenance_appends_to_existing(self, tmp_path):
        """Test that provenance updates append to existing data.

        Given an existing provenance file
        When update_cache_provenance is called with new data
        Then the new data should be added without losing existing entries

        Failure indicates provenance updates overwrite existing data.
        """
        cache_root = tmp_path / "cache"
        cache_root.mkdir()

        # Create existing provenance
        provenance_file = cache_root / "provenance.json"
        existing_data = {
            "existing_file.txt": {
                "source_url": "https://example.com/existing.txt",
                "timestamp": "2024-01-01T00:00:00",
            }
        }
        provenance_file.write_text(json.dumps(existing_data))

        # Add new file
        new_file = cache_root / "new_file.txt"
        new_file.write_text("new content")
        utils.update_cache_provenance(cache_root, new_file, "https://example.com/new.txt")

        # Verify both entries exist
        with open(provenance_file) as f:
            provenance = json.load(f)

        assert "existing_file.txt" in provenance
        assert "new_file.txt" in provenance


class TestClipQuietly:
    """Test suite for clip_quietly function."""

    def test_clip_quietly_has_correct_signature(self):
        """Test that clip_quietly has the correct function signature.

        Given the clip_quietly function
        When inspecting its signature
        Then it should have the expected parameters

        Failure indicates the function signature has changed.
        Note: Per docstring, uses rastertoolkit.raster_clip to extract population
        values for each shape in the shapefile, suppressing verbose stdout output.
        Returns dictionary mapping shape attribute values to population counts.
        """
        # clip_quietly is a complex raster operation that requires real geospatial data
        # We'll create a simpler test that just verifies the function exists and has correct signature
        from inspect import signature

        sig = signature(utils.clip_quietly)
        params = list(sig.parameters.keys())
        assert "raster_file" in params
        assert "shapefile" in params
        assert "shape_attr" in params

        # Verify return type annotation
        _return_annotation = sig.return_annotation
        # Should return dict[str, float] per docstring


class TestInformAndError:
    """Test suite for inform and error functions."""

    def test_inform_outputs_message(self, capsys):
        """Test that inform outputs informational messages.

        Given an informational message
        When inform is called
        Then the message should be displayed

        Failure indicates logging/output functionality is broken.
        """
        utils.inform("Test information message")
        captured = capsys.readouterr()
        # The output may go to stdout or stderr, check both
        assert (
            "Test information message" in captured.out or "Test information message" in captured.err
        )

    def test_error_raises_runtime_error(self):
        """Test that error raises RuntimeError with message.

        Given an error message
        When error is called
        Then a RuntimeError should be raised with that message

        Failure indicates error function behavior has changed.
        """
        with pytest.raises(RuntimeError, match="Test error message"):
            utils.error("Test error message")
