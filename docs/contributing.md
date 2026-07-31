# Contributing to `laser-init`

Thank you for your interest in contributing to `laser-init`! This guide will help you get started.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Code Style](#code-style)
5. [Testing](#testing)
6. [Documentation](#documentation)
7. [Submitting Changes](#submitting-changes)
8. [Adding Features](#adding-features)

## Code of Conduct

Be respectful, inclusive, and professional. We welcome contributors of all backgrounds and experience levels.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Fork and Clone

```shell
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/laser-init.git
cd laser-init
```

### Set Up Development Environment

```shell
# Using uv (recommended)
uv sync

# Or using pip
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Verify Setup

```shell
# Run tests
pytest

# Check code style
ruff check .

# Try the CLI
laser-init --help
```

## Development Workflow

### 1. Create a Branch

```shell
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/modifications

### 2. Make Changes

Follow the [Code Style](#code-style) guidelines.

### 3. Add Tests

All new features and bug fixes must include tests. See [Testing](#testing).

### 4. Update Documentation

- Update relevant files in `docs/`
- Add/update docstrings in code
- Update `README.md` if user-facing changes
- Add entry to `CHANGELOG.md`

The documentation is built with [MkDocs](https://www.mkdocs.org/) (Material theme,
with API reference generated from docstrings via `mkdocstrings`). To preview and
build it locally:

```shell
# Preview with live reload at http://127.0.0.1:8000
uv run mkdocs serve

# Build the static site into ./site (the same --strict build that CI runs;
# fails on broken links or references)
uv run mkdocs build --strict
```

Documentation layout:

- Prose pages live in `docs/` and are organized by the `nav` in `mkdocs.yml`.
- API reference pages live in `docs/api/` — one Markdown file per module containing
  a `::: laser.init.<module>` block that mkdocstrings renders from the docstrings.
- When you add a new module that should appear in the API reference, add a matching
  page under `docs/api/` and a `nav` entry in `mkdocs.yml`.

The docs are deployed to GitHub Pages automatically on push to `main` by
`.github/workflows/docs.yml`.

### 5. Test Your Changes

```shell
# Run all tests
pytest

# Run with coverage
pytest --cov=laser.init --cov-report=term-missing

# Run specific test file
pytest tests/test_utils.py

# Run specific test
pytest tests/test_utils.py::test_iso_from_country_string_exact_match
```

### 6. Format and Lint

```shell
# Check style issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

### 7. Commit Changes

```shell
git add .
git commit -m "Brief description of changes

Longer explanation if needed.

Fixes #123"
```

Commit message guidelines:
- Use present tense ("Add feature" not "Added feature")
- Keep first line under 72 characters
- Reference issues/PRs when relevant
- Be descriptive but concise

### 8. Push and Create Pull Request

```shell
git push --set-upstream origin <your-branch>
```

Then create a pull request on GitHub.

## Code Style

`laser-init` follows the conventions in [CLAUDE.md](https://github.com/laser-base/laser-init/blob/main/CLAUDE.md).

### General Conventions

- **Use double quotes** for strings (unless inside a quoted string)
- **Use pathlib.Path** instead of `os.path`
- **Import inform and error** from `.utils`, use `inform()` for internal actions
- **Update CHANGELOG.md** for all changes

### Python Style

- Follow PEP 8
- Line length: 100 characters
- Target Python 3.10+
- Enforced by ruff configuration in `pyproject.toml`

### Naming Conventions

- `snake_case` for functions, variables, module names
- `PascalCase` for classes
- `UPPER_CASE` for constants
- Descriptive names preferred over short names

### Example

```python
from pathlib import Path

from laser.init.utils import inform

def download_shapefile(iso_code: str, level: int, cache_dir: Path) -> Path:
    """Download shapefile for specified country and admin level.

    Downloads shapefile data from the configured source and caches it locally
    for future use.

    Args:
        iso_code: ISO 3166-1 alpha-3 country code (e.g., "KEN")
        level: Administrative level (0-4)
        cache_dir: Directory for caching downloaded files

    Returns:
        Path to the downloaded shapefile

    Raises:
        ValueError: If iso_code is invalid or level is out of range
        requests.HTTPError: If download fails
    """
    inform(f"Downloading shapefile for {iso_code}, level {level}")

    # Implementation
    url = f"https://example.com/data/{iso_code}_adm{level}.shp"
    output_path = cache_dir / f"{iso_code}_admin{level}.shp"

    # ... download logic ...

    return output_path
```

## Testing

### Test Structure

Tests use **given-when-then** style:

```python
def test_iso_from_country_string_exact_match():
    """Test exact ISO-3 code matching.

    Given: A valid ISO-3 code string
    When: iso_from_country_string is called
    Then: Returns the same ISO-3 code unchanged

    Failure implications: Basic country code recognition is broken.
    """
    # Given
    input_code = "KEN"

    # When
    result = iso_from_country_string(input_code)

    # Then
    assert result == "KEN"
```

### Test Guidelines

- **One concept per test**: Test one thing at a time
- **Clear names**: Test name should describe what is being tested
- **Docstrings required**: Explain purpose and failure implications
- **Comment ambiguities**: Note any inconsistencies or edge cases
- **Run before committing**: Ensure all tests pass

### Test Coverage

Aim for >90% code coverage. Check with:

```shell
pytest --cov=laser.init --cov-report=term-missing
```

### Test Categories

Mark tests with pytest markers:

```python
import pytest

@pytest.mark.slow
def test_large_country_processing():
    """Test processing of large countries (takes >30 seconds)."""
    pass

@pytest.mark.network
def test_download_from_unocha():
    """Test downloading from UNOCHA (requires internet)."""
    pass
```

Run specific categories:

```shell
# Skip slow tests
pytest -m "not slow"

# Only network tests
pytest -m network
```

## Documentation

### Docstring Format

Use **Google-style docstrings** formatted for Markdown:

```python
def function_name(param1: str, param2: int) -> bool:
    """One-line summary of function.

    Longer description if needed. Explain the purpose, behavior,
    and any important details.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter

    Returns:
        Description of return value

    Raises:
        ValueError: When param2 is negative
        KeyError: When required config key is missing

    Example:
        ```python
        result = function_name("test", 42)
        assert result is True
        ```
    """
    pass
```

### Documentation Files

When adding/modifying features, update relevant documentation:

- **README.md**: User-facing changes, new options
- **docs/userguide.md**: Workflows, examples
- **docs/configuration.md**: Configuration options
- **docs/datasources.md**: New data sources
- **docs/models.md**: Model changes/additions
- **docs/architecture.md**: Architectural changes
- **CHANGELOG.md**: All changes (required!)

### CHANGELOG Format

```markdown
## [Unreleased]

### Added
- New feature X that does Y (#123)
- Support for Z data source

### Changed
- Improved performance of population aggregation by 50%

### Fixed
- Fixed bug where level 0 queries failed (#456)
- Corrected population totals for disputed territories

### Deprecated
- Old API method will be removed in v1.0

### Removed
- Removed deprecated function from v0.5

### Security
- Updated dependency X to fix CVE-2024-XXXX
```

## Submitting Changes

### Pull Request Process

1. **Ensure CI passes**: All tests and checks must pass
2. **Update documentation**: All relevant docs updated
3. **Add to CHANGELOG**: Entry in [Unreleased] section
4. **Descriptive PR title**: Clear, concise description
5. **Fill out PR template**: Provide context and testing info
6. **Request review**: Tag maintainers if needed

### PR Title Format

- `feat: Add support for GADM level 4 boundaries`
- `fix: Correct population aggregation for small islands`
- `docs: Update installation instructions for Windows`
- `test: Add tests for country name fuzzy matching`
- `refactor: Simplify extractor interface`

### PR Description Template

```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes
- Change 1
- Change 2
- Change 3

## Testing
How was this tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Code formatted (ruff)
- [ ] All tests pass locally

## Related Issues
Fixes #123
Relates to #456
```

## Adding Features

### Adding a New Data Source

See [Architecture Documentation](architecture.md#adding-a-new-shapefile-source) for detailed steps.

**Summary**:
1. Create extractor in `src/laser/init/extractors/`
2. Create transformer in `src/laser/init/transformers/`
3. Register in `cli.py`
4. Add tests
5. Update documentation

### Adding a New Model Type

See [Architecture Documentation](architecture.md#adding-a-new-model-type) for detailed steps.

**Summary**:
1. Create model template in `src/laser/init/models/`
2. Update loader in `src/laser/init/loaders/`
3. Register in CLI options
4. Add tests
5. Update documentation

### Adding CLI Options

1. Add to `cli.py`:
```python
@click.option(
    "--new-option",
    type=click.Choice(["value1", "value2"]),
    default="value1",
    help="Description of new option"
)
def cli(..., new_option):
    # Handle new option
    pass
```

2. Update `config.py` if option should be configurable
3. Update documentation
4. Add tests

## Common Tasks

### Adding a Test

```shell
# Create test file if needed
touch tests/test_new_feature.py

# Write test
cat > tests/test_new_feature.py << 'EOF'
def test_new_feature():
    """Test new feature functionality.

    Given: Setup scenario
    When: Call new feature
    Then: Expected outcome

    Failure implications: New feature is broken.
    """
    # Test implementation
    assert True
EOF

# Run test
pytest tests/test_new_feature.py
```

### Running Integration Tests

```shell
# Run a full pipeline test
pytest tests/test_cli.py::test_full_pipeline_integration -v

# Test with real downloads (slow, requires network)
pytest -m "network and slow" -v
```

### Debugging

```shell
# Run with verbose output
pytest -vv tests/test_file.py

# Drop into debugger on failure
pytest --pdb tests/test_file.py

# Print output (don't capture)
pytest -s tests/test_file.py
```

## Getting Help

- **Documentation**: Check the [documentation](index.md) first
- **GitHub Issues**: Search existing issues
- **Discussions**: Use GitHub Discussions for questions
- **Architecture**: See [architecture.md](architecture.md)

## Recognition

Contributors will be recognized in:

- CHANGELOG.md (per contribution)
- README.md contributors section (after multiple contributions)
- GitHub contributors page

Thank you for contributing to `laser-init`!

---

**Last Updated**: March 2026
