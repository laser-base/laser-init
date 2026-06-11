# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed
- UNOCHA extractor now downloads per-country, per-administrative-level GeoPackage
  files (`.gpkg.zstd`) from the laser-base UNOCHA repository
  (https://github.com/laser-base/unocha), mirroring the GeoBoundaries extractor.
  The previous behavior (downloading the single global geodatabase from UNOCHA's
  Humanitarian Data Exchange) is retained as an automatic fallback when a country
  or level is not available in the repository.
  - Added extractor tests covering the repository URL, the global-dataset fallback,
    and the extract signature.
- UNOCHA transformer now dispatches on the shape file type: it zstd-decompresses and
  reads the per-country/level `.gpkg.zstd` GeoPackage (layer `UNOCHA-<ISO>-ADM<level>`)
  from the laser-base repository, and retains the existing global `.gdb.zip`
  unzip-and-filter logic as the fallback path. Unsupported formats now raise `ValueError`.
  - Added `zstandard` as an explicit dependency.
  - Added transformer tests for the repository `.gpkg.zstd` path (real decompression
    and GeoPackage I/O), the global `.zip` fallback path, unsupported-format rejection,
    and the transform signature.

### Added
- Comprehensive documentation overhaul
  - Updated pyproject.toml with proper package description
  - Completely rewrote README.md with installation instructions, prerequisites, troubleshooting, advanced usage, and comprehensive examples
  - Created docs/configuration.md: Complete configuration guide covering global config, run config, model parameters, and API keys
  - Created docs/userguide.md: Comprehensive user guide with workflows, tutorials, and best practices
  - Created docs/datasources.md: Detailed documentation of all data sources (UNOCHA, geoBoundaries, GADM, WorldPop, UN WPP) with comparison tables and selection guidance
  - Created docs/models.md: Complete epidemiological models documentation (SI, SIR, SEIR) with theory, parameters, spatial connectivity, and extension examples
  - Created docs/architecture.md: Developer documentation with system architecture, component interfaces, data flow, and extension points
  - Created docs/contributing.md: Contributing guide with development workflow, code style, testing guidelines, and PR process
  - Created docs/examples-plan.md: Comprehensive plan for examples directory with 20+ example scripts and notebooks
- Comprehensive docstring coverage across the entire codebase (100% of functions now documented)
  - Added docstrings to all extractor classes (GADM, GeoBoundaries, UNOCHA, UNWPP, WorldPop)
  - Added docstrings to all transformer classes (GADM, GeoBoundaries, UNOCHA, UNWPP)
  - Added docstrings to all loader classes (ABM, MPM)
  - Added docstrings to all CLI functions in cli.py including `transform_stats_data`
  - Added docstrings to all model script functions (SI, SIR, SEIR, plot)
  - Completed incomplete docstrings in utils.py with full parameter and return value documentation
  - Added examples to key public functions (`iso_from_country_string`, `level_from_string`)
  - Added Returns sections to all `__init__` methods (13 classes)
  - Added Raises sections to model main() functions and `download_file` utility
  - Added given-when-then style docstrings to test functions in test_gadm_extractor.py and test_geoboundaries_extractor.py
- Suppress organizePolygons() RuntimeWarning in UNOCHA transformer when loading .gdb with geopandas
- Added tqdm progress bar to UNOCHA zip extraction in UnochaTransformer
- Comprehensive test suite for `iso_from_country_string` utility function
  - Added 46 test cases for exact ISO 3166-1 alpha-3 code matching
  - Added 46 test cases for exact country name to ISO code conversion
  - Added 46 test cases for fuzzy matching of misspelled/variant country names
  - Added 20 test cases for rejecting invalid/random input strings
  - Added detailed docstrings to all test functions explaining purpose and failure implications
  - Added module-level docstring to test file
- Added build system configuration to `pyproject.toml` for proper package installation
- Added `pytest-cov` to development dependencies for test coverage reporting

### Fixed
- **CRITICAL**: Fixed runtime bugs in SI and SIR model scripts
  - Fixed `models/si.py`: Removed incorrect E and R state initialization (SI model should only have S and I states)
  - Fixed `models/si.py`: Changed config key format from hyphens to underscores to match YAML template (`data-dir` → `data_dir`, `shape-data` → `shape_data`, etc.)
  - Fixed `models/sir.py`: Removed incorrect E state initialization (SIR model should not have Exposed state)
  - Fixed `models/sir.py`: Changed config key format from hyphens to underscores to match YAML template
  - Fixed `models/si.py`: Removed exposed duration parameters (not needed for SI model)
  - Fixed `models/sir.py`: Removed exposed duration parameters (not needed for SIR model)
- Fixed invalid OpenAI model name in `openai_query.py`: changed default from "gpt-5.2" to "gpt-4o"
- Fixed bug in `transformers/unocha.py` line 75: changed `gdf["nodeid"]` to `country_gdf["nodeid"]` to correctly assign node IDs to filtered data
- Improved docstring clarity in `openai_query.py` functions (`_maybe_prefilter_candidates`, `_build_response_schema`)
- Enhanced docstrings to document side effects (e.g., `download_file` updates provenance.json)
- Clarified docstrings for unused `year` parameters in GADM and GeoBoundaries extractors
- Fixed pytest configuration error by adding missing `pytest-cov` dependency
- Fixed module import issues by configuring hatchling build backend with correct package paths
- Corrected coverage module name from `laser_init` to `laser.init` in pytest configuration
- Fixed `openai-query.py` OpenAI SDK incompatibility by switching to `responses.create(text={"format": ...})` for JSON schema structured outputs (openai==2.x)
- Removed hardcoded OpenAI API key from `openai-query.py` demo; now reads `OPENAI_API_KEY` from environment
- Added extensive inline documentation in `openai_query.py` explaining schema design and OpenAI Responses API arguments
- Improved `iso_from_country_string` matching by normalizing case/diacritics (e.g., "Sénégal") before exact/fuzzy matching
- Added explicit aliases for common French country spellings (e.g., "Chine", "Inde", "Japon")
- Added explicit alias "Estland" for Estonia (EST)
- Added French country names to name mapping.
