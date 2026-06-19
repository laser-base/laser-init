# laser-init Integration Plan — embedding & extension by downstream LASER packages

Make `laser-init` reusable by other LASER-based packages so they can add/override
data sources, options, and defaults, and — the headline requirement — **ship their
own sample model scripts**, all **without losing or changing the basic
`laser-init` command-line interface**.

## 1. Goals & invariants

**Goals**
- A downstream package (e.g. a disease-specific `laser-measles`) can:
  - register additional or replacement data sources (shape/raster/stats),
  - register its **own model templates** (the model script(s) + config it emits),
  - set its own defaults (default model, sources, output layout) and optionally add CLI options,
  - do all of the above by *installing* alongside `laser-init` (no fork, no edits to laser-init).

**Hard invariants**
- The stock `laser-init` console script keeps working **unchanged** with the built-in
  sources/models when no plugins are installed.
- `laser-init` has **no dependency** on any downstream package (extension is one-directional).
- Existing behavior, defaults, and the 176-test suite stay green.

## 2. Where we are today (grounding in the current code)

- **Entry point:** `pyproject.toml` → `laser-init = "laser.init.cli:cli"`.
- **Pipeline is already decomposed** into module-level functions in `cli.py`, called in
  sequence by `cli()`: `validate_arguments` → `download_shape_data` /
  `download_raster_data` / `download_demographic_stats` → `transform_shape_and_raster_data`
  / `transform_stats_data` → `emit_model_script` → `write_plots`. This makes a library
  seam cheap to extract.
- **Registry** (`laser.init.registry`): dicts `SHAPE_SOURCES`, `RASTER_SOURCES`,
  `STATS_SOURCES`, `MODEL_LOADERS`, the `ShapeSource`/`StatsSource` dataclasses, and
  `get_*` lookups. Already the single dispatch point.
- **Interfaces** (`laser.init.interfaces`): `@runtime_checkable` Protocols —
  `ShapeExtractor`, `RasterExtractor`, `StatsExtractor`, `ShapeTransformer`,
  `StatsTransformer`, `ModelLoader`.
- **Loaders** (`loaders/abm.py`, `loaders/mpm.py`): `emit_script(mode, model, shape,
  cxr, pop, exp, output_dir)`.

**The blockers for downstream model scripts (today):**
1. `AbmLoader.emit_script` resolves model scripts from **laser-init's own package**:
   `shutil.copy2(Path(__file__).parent.parent / "models" / f"{model.lower()}.py", ...)`
   (and copies `plot.py`). A downstream package cannot inject its own script here.
2. The config is a **hardcoded `__yaml__`** string in `abm.py` (fixed `simulation:` keys).
3. CLI `--model`/`--mode`/`--*-source` are **hardcoded `click.Choice([...])`** lists;
   `--model` names (`SI/SIR/SEIR`) aren't represented in the registry at all.
4. The registry is **read-only** (module-level dict literals; no public `register_*`).

## 3. Two integration patterns (complementary)

### Pattern A — Plugin mode (zero end-user code)
Downstream installs next to `laser-init` and registers its sources/models via Python
**entry points**. End users keep typing `laser-init ... --model <downstream-model>` and
the new choices appear automatically. The CLI is unchanged; its option choices grow.

### Pattern B — Embed / wrapper mode (downstream owns the CLI)
Downstream ships its own console script (e.g. `measles-init`) that reuses laser-init's
pipeline and registry, sets its own defaults, and ships its own model templates —
built from a public `run_pipeline()` + `build_cli()` factory. The stock `laser-init`
command still exists unchanged for anyone who installs only laser-init.

## 4. Core design changes

### 4.1 Public, mutable registry API
Add register/list functions; register the built-ins through them at import:
```python
register_shape_source(name, extractor, transformer, *, override=False)
register_raster_source(name, extractor, *, override=False)
register_stats_source(name, extractor, transformer, *, override=False)
register_model_loader(mode, loader, *, override=False)
register_model(template)                      # see 4.2
list_shape_sources() / list_raster_sources() / list_stats_sources()
list_modes() / list_models()
```
- `override=False` raises on name collision (protects built-ins); explicit override allowed.
- `get_*` lookups stay; `list_*` feeds dynamic CLI choices (4.4).
- Each registered component is checked against its Protocol (`isinstance`, runtime_checkable)
  with a clear error for plugin authors.

### 4.2 First-class `ModelTemplate` — the headline capability
Generalize "a model" from "a `{name}.py` file in laser-init's `models/` dir + the abm
`__yaml__`" into a registrable object owned by *any* package:
```python
@dataclass(frozen=True)
class ModelTemplate:
    name: str                  # e.g. "seir" or downstream "measles"
    mode: str                  # which loader/mode it belongs to (e.g. "abm")
    package: str               # owning package for importlib.resources (e.g. "laser.measles.templates")
    script: str                # primary script resource, e.g. "measles.py"
    extra_files: tuple[str, ...] = ()   # companions, e.g. ("plot.py",)
    config_template: str | None = None  # resource name OR inline template string
    config_defaults: dict | None = None # default simulation params / keys
    min_laser_generic: str | None = None  # advisory version guard
```
- New registry: `MODEL_TEMPLATES: dict[str, ModelTemplate]`; `register_model(template)`.
- **`AbmLoader.emit_script` is refactored** to: look up the selected template by
  `model`, materialize *its* files via `importlib.resources.files(template.package)`
  (NOT laser-init's `models/` dir), and render config from *its* `config_template` /
  `config_defaults` (replacing the hardcoded `__yaml__`).
- laser-init's `SI`/`SIR`/`SEIR` become **built-in `ModelTemplate`s** (package
  `laser.init.models`), registered at import → identical behavior, no special-casing.
- This is exactly what lets a downstream package "provide its own sample model scripts":
  it registers a `ModelTemplate` pointing at files in its own package.
- **Ties to laser-generic issue
  [#195](https://github.com/laser-base/laser-generic/issues/195):** once the immunization
  components are fixed upstream, a "seir + vaccination" model script becomes just another
  `ModelTemplate` a package can ship — and the deferred `examples/model_customization/add_vaccination.py`
  can be revisited as one.

### 4.3 Plugin discovery via entry points
- Define group `laser_init.plugins`. Each entry point is a callable that performs
  registrations (calls `register_*`), e.g.:
  ```toml
  # downstream pyproject.toml
  [project.entry-points."laser_init.plugins"]
  measles = "laser.measles.laser_init_plugin:register"
  ```
- `laser.init.plugins.load_plugins()` discovers via
  `importlib.metadata.entry_points(group="laser_init.plugins")`, imports, and calls each
  `register()`. **Resilient:** a failing plugin is logged (via `logger`/`inform`) and
  skipped, never crashing the CLI. Idempotent (load-once guard).
- Called once at CLI startup and exposed for library users.

### 4.4 Dynamic CLI choices (keeps the basic CLI, makes it extensible)
- Build `--mode` / `--model` / `--*-source` choices from the registry **after**
  `load_plugins()`, instead of hardcoded lists. Either a registry-backed `click.Choice`
  subclass that reads `list_*()` lazily, or construct the command in `build_cli()` after
  discovery.
- With no plugins installed, choices == today's built-ins → identical `--help` and behavior.

### 4.5 Library-callable pipeline + CLI factory
- Extract the orchestration body of `cli()` into:
  ```python
  def run_pipeline(country, level, start_year, end_year, *, output_dir=None,
                   mode="ABM", model="SEIR", shape_source=None,
                   raster_source=None, stats_source=None) -> PipelineResult
  ```
  returning the produced paths (shape gpkg, csvs, model script, plots). `cli()` becomes a
  thin click wrapper over it.
- Add a factory so downstream can mint their own command without re-implementing anything:
  ```python
  def build_cli(*, prog_name="laser-init", defaults=None, extra_options=None) -> click.Command
  ```
  Downstream: `measles-init = "laser.measles.cli:main"` where
  `main = laser.init.build_cli(prog_name="measles-init", defaults={"model": "measles", "mode": "abm"})`.

### 4.6 Defaults & config precedence
Allow plugins to contribute default mode/model/source (so a downstream package's model can
be *the* default). Keep precedence: **explicit CLI > config file (`laser_config.yaml`) >
plugin-contributed defaults > built-in defaults.**

## 5. Public API surface (`laser.init.__init__`)
Export and document as stable: `register_shape_source`, `register_raster_source`,
`register_stats_source`, `register_model`, `register_model_loader`, `list_*`,
`run_pipeline`, `build_cli`, `load_plugins`, `ModelTemplate`, and the `interfaces`
Protocols. Everything else stays internal.

## 6. Backwards compatibility
- `laser-init` script unchanged; identical output with built-ins and no plugins.
- Registry `get_*` and the module-level dicts remain (dicts become views/backed by the
  register API) so internal callers and existing tests don't break.
- `ModelLoader` Protocol unchanged; `AbmLoader.emit_script` keeps its signature
  (`mode, model, ...`) and simply consults `MODEL_TEMPLATES[model]` internally.
- Regression test pins the stock CLI's choices and a no-plugin run to current behavior.

## 7. Testing strategy
- **In-repo sample plugin fixture** (`tests/fixtures/sample_plugin/`) that registers a
  custom shape source and a custom `ModelTemplate` (with its own tiny script + config).
  Assert: it appears in `list_*`/CLI choices; `--model <custom>` materializes the
  downstream script + config; `run_pipeline(model=<custom>)` works.
- **Entry-point discovery** test (monkeypatch `entry_points`) + **resilient-failure**
  test (a broken plugin is logged and skipped, CLI still runs).
- **Registry** tests: register, override guard, Protocol-conformance rejection, `list_*`.
- **ModelTemplate** test: files resolved from the owning package via `importlib.resources`.
- **CLI invariant** test: no-plugin choices/`--help` match the current baseline.
- Keep all current tests green.

## 8. Documentation
- New `docs/integration.md` ("Extending laser-init"): both patterns, the entry-point
  contract, a complete worked downstream example (pyproject entry point + `register()` +
  a `ModelTemplate`), and the public API reference. Add to mkdocs nav.
- Update `docs/architecture.md` (extension points), `docs/contributing.md`, and add API
  pages for `registry`, `interfaces`, and `plugins`.

## 9. Phased roadmap (each phase independently shippable; invariant held throughout)
- **Phase 0 — Library seam.** Extract `run_pipeline`; `cli` becomes a wrapper. No behavior change.
- **Phase 1 — Registry write API.** `register_*` + `list_*`; built-ins registered via them; dicts kept as views. Tests.
- **Phase 2 — ModelTemplate (headline).** Add the abstraction; convert SI/SIR/SEIR to built-in templates; refactor `AbmLoader` to materialize the selected template's files from its owning package; derive `--model` choices from the registry.
- **Phase 3 — Plugin discovery.** `laser_init.plugins` entry-point group + resilient `load_plugins()`; wire into CLI startup.
- **Phase 4 — Dynamic choices + `build_cli` factory + plugin/config defaults.**
- **Phase 5 — Docs, sample plugin, CI** (extend the examples/plugin static checks; add a plugin smoke test).

## 10. Minimum viable version
If a small first cut is preferred: **Phase 0 + Phase 2's `ModelTemplate`/`register_model`
+ `AbmLoader` change**. That alone delivers "a downstream package provides its own model
scripts" (register a template, select with `--model`) while the CLI is untouched.
Entry-point auto-discovery (Phase 3) and the `build_cli` factory (Phase 4) are the
convenience layers that make it seamless.

## 11. Risks & open questions
- **Model-script ↔ laser-generic coupling.** Templates embed laser-generic API usage;
  upstream protocol/version drift can break downstream templates (cf.
  [laser-generic#195](https://github.com/laser-base/laser-generic/issues/195)). Mitigate:
  templates own their code (laser-init only materializes files + config) and declare a
  `min_laser_generic` advisory version.
- **Per-template config schema.** Downstream models need different `simulation:` keys, so
  the single hardcoded `__yaml__` must become per-template config (template-owned). Consider
  light schema validation and a documented set of "standard" keys
  (`data_dir`, `datafiles`, …) the pipeline guarantees.
- **Startup cost & trust.** Importing plugins on every CLI invocation adds import time and
  a failure surface — keep discovery resilient (skip-on-error, log) and consider an opt-out
  env var.
- **Dynamic `--help`.** Option choices vary with installed plugins; acceptable but document it.
- **API/Protocol versioning.** Semver the extension surface; `@runtime_checkable` only
  checks attribute names, so provide a `check_conformance()` helper for plugin authors and
  consider signature checks in tests.
- **MPM still unimplemented.** `MpmLoader` is a placeholder; the template mechanism should
  not assume every mode is functional (register only working modes; clear error otherwise).

---
**Status:** proposal / not yet implemented.
**Owning files if pursued:** `registry.py`, `interfaces.py`, new `plugins.py`,
`loaders/abm.py`, `cli.py`, `__init__.py`, `pyproject.toml` (entry-point group),
`docs/integration.md`.
