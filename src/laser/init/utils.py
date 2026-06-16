"""
Utility functions for the laser.init package.

Using the [RapidFuzz package](https://rapidfuzz.github.io/RapidFuzz/) for fuzzy string matching to convert country names to ISO codes.

- Initial näive choice, use Damerau-Levenshtein distance, which allows for transpositions, as well as insertions, deletions, and substitutions.

"""

import contextlib
import io
import json
import unicodedata
import warnings
from datetime import datetime
from pathlib import Path
from typing import NoReturn

import click
import pycountry
import rastertoolkit as rtk
import requests
from tqdm import tqdm

from .config import configuration as config
from .config import default_cache_directory
from .french_iso import french_mapping as __french_mapping__
from .logger import logger


def _normalize_string(value: str) -> str:
    """Normalize a country string for matching.

    Applies Unicode normalization to handle accents and diacritics, performs
    case-folding for better case-insensitive matching, and strips whitespace.

    Args:
        value: The string to normalize (typically a country name).

    Returns:
        Normalized string suitable for case-insensitive fuzzy matching.

    Notes:
        - Unicode NFKD + drop combining marks: makes accents/diacritics comparable.
        - Casefold: more aggressive (and correct) case normalization than lower().
        - Strip: removes surrounding whitespace.
    """

    decomposed = unicodedata.normalize("NFKD", (value or "").strip())
    no_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return no_marks.casefold()


__iso_codes__ = {
    _normalize_string(country.alpha_3): country.alpha_3 for country in pycountry.countries
}

__name_mapping__ = {
    _normalize_string(country.name): country.alpha_3 for country in pycountry.countries
}

__name_mapping__.update(
    {_normalize_string(key): value for key, value in __french_mapping__.items()}
)

__name_mapping__.update(
    {
        _normalize_string(country.official_name): country.alpha_3
        for country in pycountry.countries
        if hasattr(country, "official_name")
    }
)

__name_mapping__.update(
    {
        "bonaire": "BES",
        "bolivia": "BOL",
        "congo": "COG",
        "micronesia": "FSM",
        "iran": "IRN",
        "korea": "KOR",
        "moldova": "MDA",
        "palestine": "PSE",
        "saint helena": "SHN",
        "taiwain": "TWN",
        "tanzania": "TZA",
        "venezuela": "VEN",
    }
)


def iso_from_country_string(input_string: str) -> str | None:
    """Convert a country name to its ISO 3166-1 alpha-3 code.

    Performs normalized matching against ISO codes, country names (including
    official names), and French country names. If no exact match is found,
    attempts fuzzy matching using pycountry.

    Args:
        input_string: Country name or ISO code to convert (e.g., "Nigeria", "nga", "Nigéria").

    Returns:
        ISO 3166-1 alpha-3 code (e.g., "NGA"), or None if no match found.

    Examples:
        >>> iso_from_country_string("Nigeria")
        "NGA"
        >>> iso_from_country_string("République démocratique du Congo")
        "COD"
        >>> iso_from_country_string("USA")
        "USA"
    """
    normalized = _normalize_string(input_string)
    logger.info(
        f"iso_from_country_string(): Normalized input string '{input_string}' to '{normalized}'."
    )

    if normalized in __iso_codes__:
        iso3 = __iso_codes__[normalized]
        logger.info(
            f"iso_from_country_string(): Found exact ISO code match for '{normalized}': {iso3}"
        )
        return iso3
    elif normalized in __name_mapping__:
        iso3 = __name_mapping__[normalized]
        logger.info(f"iso_from_country_string(): Found exact name match for '{normalized}': {iso3}")
        return iso3

    if len(normalized) < 4:
        inform(
            f"iso_from_country_string(): Input string '{input_string}' is too short for reliable matching."
        )
        return None

    try:
        options = pycountry.countries.search_fuzzy(normalized)
        if options:
            matches = "\n\t".join(f"{country.name} (ISO: {country.alpha_3})" for country in options)
            warnings.warn(f"Possible match(es):\n\t{matches}", stacklevel=2)
    except LookupError:
        pass

    inform(f"iso_from_country_string(): No matches found for '{input_string}'.")
    return None


def level_from_string(input_string: str) -> int | None:
    """Convert a level string to a standardized administrative level number.

    Parses strings in the format 'admin1', 'ADM2', or '3' and returns the
    corresponding administrative level number.

    Args:
        input_string: Level string to parse (case-insensitive, accepts "admin1",
            "ADM2", "3", etc.).

    Returns:
        Administrative level number (0-4), or None if parsing fails or value
            is out of range.

    Examples:
        >>> level_from_string("admin1")
        1
        >>> level_from_string("ADM2")
        2
        >>> level_from_string("3")
        3
    """

    lowered = input_string.lower().strip()

    # Valid strings start with "admin" or "adm", followed by a number, or just a number
    if lowered.startswith("admin"):
        number_part = lowered[5:]
    elif lowered.startswith("adm"):
        number_part = lowered[3:]
    else:
        number_part = lowered

    # Validate that number_part is a single digit between 0 and 4
    if number_part.isdigit():
        level_num = int(number_part)
        if 0 <= level_num <= 4:
            logger.info(
                f"level_from_string(): Parsed level number {level_num} from input '{input_string}'."
            )
            return level_num

    logger.info(f"level_from_string(): No matches found for '{input_string}'. Returning None.")
    return None


def download_file(
    url: str,
    cache_dir: Path,
    dest_dir: Path,
    local_name: str = None,
    show_progress: bool = True,
    force: bool = False,
) -> Path:
    """Download a file from a URL and save it to the specified directory.

    The function streams the file in chunks, displays a progress bar if enabled.
    If the file already exists and force is False, the existing file is returned without downloading.

    Args:
        url: The URL of the file to download.
        cache_dir: The root cache directory (used for provenance tracking).
        dest_dir: The subdirectory within cache_dir where the file will be saved.
        local_name: The name to use for the saved file. If None, uses the filename from the URL.
        show_progress: If True, display a progress bar during download (default: True).
        force: If True, download even if the file already exists (default: False).

    Returns:
        Path to the downloaded file.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request fails.
        requests.exceptions.RequestException: For other network-related errors.

    Side Effects:
        Updates provenance.json in cache_dir with download metadata (URL, timestamp).
    """

    local_name = local_name or url.split("/")[-1]
    local_path = cache_dir / dest_dir / local_name

    if local_path.exists() and not force:
        inform(f"File already exists: {local_path}. Use force=True to re-download.")
        return local_path

    inform(f"Downloading file from {url} to {local_path}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total = int(response.headers.get("content-length", 0))
    chunk_size = 8192

    if total > 0 and show_progress:
        progress = tqdm(total=total, unit="B", unit_scale=True, desc=local_name)

    with local_path.open("wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                if show_progress:
                    progress.update(len(chunk))

    if show_progress:
        progress.close()

    update_cache_provenance(cache_dir, local_path, url)
    inform(f"File downloaded successfully: {local_path}")

    return local_path


def update_cache_provenance(cache_root: Path, file_path: Path, source_url: str) -> None:
    """Update the provenance log with information about a downloaded file.

    Creates or updates provenance.json in the cache root directory with metadata
    about downloaded files, including source URLs and timestamps.

    Args:
        cache_root: The root directory for cached data.
        file_path: The path to the downloaded file.
        source_url: The URL from which the file was downloaded.

    Returns:
        None
    """
    provenance_file = cache_root / "provenance.json"
    provenance = json.loads(provenance_file.read_text() if provenance_file.exists() else "{}")

    timestamp = datetime.now().isoformat()
    provenance.update({file_path.name: {"source_url": source_url, "timestamp": timestamp}})

    with provenance_file.open("w") as f:
        json.dump(provenance, f, indent=4)

    inform(f"Cache provenance updated: {file_path.name} from {source_url} at {timestamp}")

    return


def update_local_provenance(output_dir: Path, output_filename: Path, *files: list[Path]) -> None:
    """Update local provenance for transformed files.

    Tracks which cached source files were used to create each transformed output file
    by copying provenance records from cache provenance.json to local provenance.json.

    Args:
        output_dir: Directory where the output file and local provenance.json are located.
        output_filename: Path to the output file being tracked.
        *files: Variable number of Path objects representing source files from cache.

    Returns:
        None
    """
    cache_root = Path(config.get("cache_dir", default_cache_directory))
    provenance_file = cache_root / "provenance.json"
    sources = json.loads(provenance_file.read_text())
    provenance_local = output_dir / "provenance.json"
    provenance = json.loads(provenance_local.read_text() if provenance_local.exists() else "{}")
    records = {file.name: sources[file.name] for file in files}
    provenance.update({output_filename.name: records})
    with provenance_local.open("w") as file:
        json.dump(provenance, file, indent=4)

    inform(
        f"Local provenance updated: {output_filename.name} from {', '.join(file.name for file in files)}"
    )

    return


def clip_quietly(raster_file: Path, shapefile: Path, shape_attr: str) -> dict[str, float]:
    """Clip a raster file using a shapefile while suppressing stdout output.

    Uses rastertoolkit.raster_clip to extract population values for each shape
    in the shapefile, redirecting stdout to suppress verbose output.

    Args:
        raster_file: Path to the population raster file (GeoTIFF).
        shapefile: Path to the shapefile containing administrative boundaries.
        shape_attr: Attribute name in the shapefile to use as dictionary keys.

    Returns:
        Dictionary mapping shape attribute values to population counts.
    """
    inform(
        f"Clipping raster_file={raster_file} with shapefile={shapefile}, shape_attr={shape_attr}..."
    )
    with contextlib.redirect_stdout(io.StringIO()):
        pop_dict = rtk.raster_clip(raster_file, shapefile, shape_attr=shape_attr)
    inform(f"Clipped raster_file={raster_file}.")

    return pop_dict


def inform(msg: str) -> None:
    """Display an informational message to the user and log it.

    Args:
        msg: The message to display and log.

    Returns:
        None
    """
    click.echo(msg)
    logger.info(msg)

    return


def error(msg: str, exception: Exception = RuntimeError) -> NoReturn:
    """Display an error message, log it, and raise an exception.

    Args:
        msg: The error message to display and log.
        exception: Exception class or instance to raise (default: RuntimeError).

    Raises:
        Exception: The exception type specified in the exception parameter.
    """
    click.echo(click.style(msg, fg="red"))
    logger.error(msg)

    raise exception(msg) if isinstance(exception, type) else exception
