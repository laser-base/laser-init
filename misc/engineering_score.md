# Project Engineering Score

- **Project**: `/Users/christopherlorton/projects/laser-fresh/laser.init`
- **Tier**: 1 (Software library or digital public good used by many people for many years)
- **Overall Score**: 74/100
- **Status**: PASS
- **Date**: 2026-05-13
- **Version**: idm-eng-plugin:eng-quality-checker v1.3_2026.04.13
- **Time spent**: 156s

## Summary

| Category | Score | Weight |
| -- | -- | -- |
| Quality | 74/100 | 40% |
| Usability | 73/100 | 40% |
| Safety | 78/100 | 20% |
| **Total** | **74/100** | 100% |

| Metric | Score | Notes |
| -- | -- | -- |
| correct | 7/10 | Good tests (~82% coverage) in given-when-then style, but no CI/CD pipeline runs them; cli.py plotting code at 57.8% coverage; default simulation parameters not cited to literature. |
| clear | 9/10 | Clean ETL architecture with Google-style docstrings throughout; only minor gaps (missing module docstring in `loaders/abm.py`, terse docstring in `transformers/gadm.py`). |
| concise | 7/10 | 63 ruff violations (E501 line-too-long, 5 F841 unused vars in tests, unsorted imports); si/sir/seir model templates share boilerplate. |
| simple | 8/10 | Single CLI command with sensible defaults, input validation, click error messages; fuzzy matching silently warns instead of suggesting alternatives. |
| powerful | 7/10 | Major assumptions are CLI/YAML-configurable and ETL stages are pluggable, but no abstract base classes or `**kwargs` extension hooks; WorldPop silently fails outside 2000–2030. |
| performant | 6/10 | Raster work delegated to rastertoolkit and pandas vectorization used, but no benchmarks, no profiling, no parallelization for downloads or batch country processing. |
| documented | 8/10 | README, user guide, quickstart, architecture, contributing, and configuration docs; Google-style docstrings on public APIs; missing per-subfolder READMEs, tutorials/notebooks, and the referenced `examples/` directory. |
| accessible | 7/10 | Public GitHub repo, MIT LICENSE, CHANGELOG, contributing guide, `pip install -e .` / `uv sync` in 1–2 commands; not on PyPI, no standalone CODE_OF_CONDUCT, no MCP/skills. |
| compliant | 9/10 | MIT license, no exposed secrets/PII, all deps in uv.lock are BSD/MIT (no GPL/AGPL); CHANGELOG and contributing guide present; minor deduction for git-sourced rastertoolkit lacking a verifiable license entry in the lock file. |
| reproducible | 6/10 | Dependencies specified with lower bounds in pyproject.toml and a uv.lock for reproducible installs, but no semver git tags and not published on PyPI. |

This is a well-engineered, well-documented data pipeline with a clean ETL architecture and thorough Google-style docstrings. The strongest areas are clarity (9/10), compliance (9/10), and documentation (8/10). The biggest gaps holding it back from Tier 1 are the lack of a CI pipeline running the test suite, no semantic-version git tags or PyPI release, no performance benchmarks or parallelization, and ruff style violations across the source tree.

## Recommendations

1. **[correct] — Add a CI workflow that runs the test suite on push/PR** *(effort: quick; automated: yes)*
   Add `.github/workflows/test.yml` that installs the project with `uv sync`, runs `pytest --cov=laser_init --cov-report=term --cov-fail-under=80` on Ubuntu and macOS for Python 3.11+, and runs `ruff check .` as a lint gate. This is the single highest-impact change (weight 7) and converts the existing 82% local coverage into a verified gate.

2. **[reproducible] — Tag a semantic version and publish to PyPI** *(effort: medium; automated: partial)*
   Tag `v0.1.0` with `git tag -a v0.1.0 -m "..."`, add a GitHub Action that builds and publishes on tag push (use `pypa/gh-action-pypi-publish`), and link the CHANGELOG release notes from each tag. Publishing turns the lock file + version into a reproducible distribution channel and unlocks the Tier 1 "published" rubric points.

3. **[performant] — Add benchmarks and parallelize the per-country pipeline** *(effort: medium; automated: yes)*
   Add `pytest-benchmark` cases for the raster-clip and UNWPP transform paths, capturing wall-clock baselines for a representative country (e.g. NGA). For batch runs over multiple countries, parallelize the download and transform stages with `concurrent.futures.ThreadPoolExecutor` for I/O and `ProcessPoolExecutor` for CPU-bound transforms.

4. **[correct] — Raise cli.py coverage above 80% by testing the plotting functions** *(effort: medium; automated: yes)*
   Use `matplotlib.use("Agg")` in a pytest fixture and write tests that invoke `write_plots` and each `plot_*` helper with a small fixture dataset, asserting that PNG files are produced with non-zero size and that the figure objects have the expected number of axes. This closes the 57.8% coverage gap.

5. **[documented] — Create the `examples/` directory and a runnable tutorial notebook** *(effort: medium; automated: no)*
   Replace `examples-plan.md` with an actual `examples/` folder containing at minimum a Jupyter notebook walking through `laser-init NGA 2 2000 2025`, inspecting the outputs, and showing a downstream plotting cell. Add per-subfolder READMEs in `extractors/`, `transformers/`, `loaders/`, and `models/` describing each component's contract.

6. **[concise] — Resolve the 63 ruff violations and add ruff to CI** *(effort: quick; automated: yes)*
   Run `ruff check --fix .` to auto-fix import sorting and unused-variable issues, manually wrap the E501 long lines, then add `ruff check .` and `ruff format --check .` to the CI workflow from recommendation 1 so violations cannot reaccumulate.

7. **[powerful] — Introduce abstract base classes for extractors, transformers, and loaders** *(effort: medium; automated: yes)*
   Define `BaseExtractor`, `BaseTransformer`, `BaseLoader` in `laser_init/base.py` with abstract methods that the current concrete classes already implement. This makes the extension contract explicit, enables `isinstance` checks, and supports `**kwargs` passthrough for subclass-specific options.

8. **[simple] — Replace silent warnings with actionable errors and suggestions** *(effort: quick; automated: no)*
   In `iso_from_country_string`, when fuzzy matching returns `None`, raise a `click.UsageError` listing the top-3 nearest matches via `difflib.get_close_matches`. In `config.py`, only warn once per process (or downgrade to INFO) when no config file is found, since the default behavior is fine.

9. **[accessible] — Add CODE_OF_CONDUCT.md and a CLAUDE.md/MCP entry point** *(effort: quick; automated: no)*
   Split the existing code-of-conduct text out of `docs/contributing.md` into a top-level `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1). The `CLAUDE.md` file is already present; consider adding a small `.claude/` skills directory describing the `laser-init` CLI invocation pattern for AI-assisted use.

10. **[clear] — Fill the small docstring gaps** *(effort: quick; automated: no)*
    Add a module-level docstring to `loaders/abm.py` explaining what an ABM-format output is and the structure it writes. Expand `transformers/gadm.py`'s one-line module docstring to cover inputs, outputs, and the geometry simplification step.

11. **[compliant] — Document the rastertoolkit dependency's license** *(effort: quick; automated: no)*
    Since `rastertoolkit` is fetched from a git ref, add a short note in `docs/contributing.md` or `pyproject.toml` comment citing its upstream license (MIT, per the IDM repo) so downstream packagers can verify license compatibility without inspecting the git repo.

12. **[correct] — Add literature citations for default simulation parameters** *(effort: quick; automated: no)*
    In `docs/configuration.md` (and the `abm.py` config template comment), cite the source for the default `gravity_k=500`, `gravity_a=1`, `gravity_b=1`, `gravity_c=2`, and `r0=2.5` values. Even short citations ("gravity exponents from Tatem et al. 2012; R0 from Strebel et al. 2011 for measles") move the score toward the "peer-reviewed" Tier 1 anchor.

## Full Results

```yaml
project: /Users/christopherlorton/projects/laser-fresh/laser.init
tier: 1
overall_score: 74
failed: false
quality:
  correct:
    score: 7
    weight: 7
    reason: "Good tests (~82% statement coverage) with clear given-when-then structure covering all major workflows, but there is no CI/CD pipeline for running tests (only a docs-deployment workflow exists), and cli.py has only 57.8% coverage with the plotting functions entirely untested. Default simulation parameters in the config template (gravity_k=500, r0=2.5, nyears=2) are documented in docs but not cited to literature, and no peer-review evidence is present."
  clear:
    score: 9
    weight: 2
    reason: "Clean ETL architecture (extractors/transformers/loaders/models) with descriptive names throughout; every public function has a Google-style docstring with Args, Returns, and Raises; only minor gaps include a missing module-level docstring in loaders/abm.py and a one-line module docstring in transformers/gadm.py."
  concise:
    score: 7
    weight: 1
    reason: "63 ruff violations found (primarily E501 line-too-long, 5 F841 unused-variable assignments in tests, and unsorted imports); the si.py/sir.py/seir.py model templates share identical data-loading boilerplate but are intentionally user-editable outputs so the duplication is partially justified, though a shared base would reduce it."
usability:
  simple:
    score: 8
    weight: 3
    reason: "The primary UI is a single CLI command (`laser-init NGA 2 2000 2025`) with sensible defaults (SEIR, ABM, unocha), good input validation (ISO fuzzy matching, year range checks, admin level parsing), and colored error messages via click. The main gap is that fuzzy matching silently returns None and emits a warnings.warn instead of a user-visible error suggestion, and the config module emits a warnings.warn on every run without a config file."
  powerful:
    score: 7
    weight: 2
    reason: "All major assumptions are configurable via CLI options (model type SI/SIR/SEIR, mode ABM/MPM, shape/raster/stats sources, output directory) and through a YAML/JSON config file. The extractor/transformer/loader architecture is modular and documented, but the classes themselves lack abstract base classes or **kwargs extension hooks, and the WorldPop extractor silently fails for years outside 2000-2030 without fallback."
  performant:
    score: 6
    weight: 2
    reason: "The primary computation (raster clipping to administrative boundaries) is delegated to rastertoolkit rather than a naive Python loop, and pandas vectorization is used throughout the UNWPP transformer. However, there are no performance tests or benchmarks, no profiling infrastructure, and no parallelization for the multi-step pipeline despite downloads being network-bound and transform steps being CPU-bound."
  documented:
    score: 8
    weight: 2
    reason: "Documentation is comprehensive: README covers installation, quick start, CLI options, configuration, output files, troubleshooting; docs/ contains a user guide, quickstart, datasources comparison, models, architecture, contributing, and configuration guides; all major classes and public functions have Google-style docstrings. Gaps: no per-subfolder READMEs, no interactive notebooks or tutorials, and the examples/ directory referenced in docs does not yet exist (only examples-plan.md)."
  accessible:
    score: 7
    weight: 1
    reason: "The project has a public GitHub repo, MIT LICENSE, CHANGELOG.md, a contributing guide in docs/contributing.md, and a pyproject.toml with hatchling build backend enabling pip install -e . or uv sync in 1-2 commands. It is not published on PyPI, there is no standalone CODE_OF_CONDUCT.md at the repo root, and no MCP server or skills definitions."
safety:
  compliant:
    score: 9
    weight: 6
    reason: "MIT license is present, no exposed secrets or PII found in source files, and all identified dependencies (click, geopandas, pandas, requests, etc.) carry permissive BSD/MIT licenses with no GPL/AGPL packages in uv.lock; CHANGELOG.md and docs/contributing.md are both present. Minor deduction for the git-sourced rastertoolkit dependency which lacks a verifiable license in the lock file."
  reproducible:
    score: 6
    weight: 4
    reason: "Dependencies are fully specified with lower-bound version pins in pyproject.toml and a uv.lock file ensures reproducible installs, but there are no semantic version git tags (git tag -l returns nothing) and the package is not published on PyPI (returns 404); the project version is declared as 0.1.0 in pyproject.toml only."
```
