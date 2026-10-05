# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## What this is

`csspin` is the core Python package shipping `spin`, a task runner and CLI that
provisions development environments (Python, Node, etc.) and standardizes
project workflows via a plugin system. This repo is the core/bootstrap layer
only; most actual functionality (Python tooling, Node/frontend, Java, docs,
workflows) lives in separate sibling repos named `csspin-*` (e.g.
`csspin-python`, `csspin-frontend`, `csspin-docs`, `csspin-workflows`), all
living flat under the same GitLab group as this repo, one clone per package.

`csspin` is self-hosted: this repo has its own `spinfile.yaml` and uses `spin`
to provision, test, and build itself.

## Common commands

Everything runs through `spin` once provisioned (`spinfile.yaml` declares
`csspin_python.pytest`, `csspin_python.uv_provisioner`, `csspin_docs.sphinx`,
`csspin_workflows.stdworkflows`):

- `spin provision` — set up the dev environment (installs Python, plugin
  packages, and project dependencies into `.spin/venv`). Re-run after changing
  `plugin_packages`, `plugin_paths`, or `plugins` in `spinfile.yaml`.
- `spin test` — run the full test suite via the `test` workflow hook
  (equivalent to `spin pytest` under `csspin_workflows.stdworkflows`). CI runs
  `spin test -vv --coverage --with-test-report`.
- `spin pytest <args>` — invoke pytest directly with arbitrary args, e.g. a
  single test: `spin pytest tests/test_cli.py::test_name`.
- `spin docs` — build the Sphinx documentation (`doc/`), including
  regenerating `doc/schemaref.rst` from `src/csspin/schema.yaml` via the
  `schemadoc` task (see `build_rules` in `spinfile.yaml`).
- `spin cleanup` (`--purge` to also remove `{spin.data}`) — remove
  provisioned, project-local resources.
- `spin --dump` — print the fully resolved configuration tree along with the
  file/line each value came from; the primary tool for debugging
  configuration and plugin-loading issues.
- `prek run` (or `pre-commit run`) — black, isort, prettier, flake8, pylint,
  mypy, and misc hygiene hooks (`.pre-commit-config.yaml`). pylint/mypy
  exclude `tests/` and `plugins/`.

Pytest markers: `slow` (excluded by default via `pytest.opts: [-m, "not
slow"]` in `spinfile.yaml`) and `wip`.

## Architecture

### Bootstrapping and the config tree

`spin`'s entire behavior is driven by one nested, ordered-dict-like structure:
the **configuration tree** (`csspin.tree.ConfigTree`, in `src/csspin/tree.py`).
Every plugin's settings, `spinfile.yaml` contents, CLI overrides, and even
spin's own bootstrap state (`cfg.spin.*`) live in this single tree, accessed
both as `cfg["key"]` and `cfg.key`. `ConfigTree` tracks, per key, the source
file/line the value came from — this is what powers `spin --dump`.

Startup sequence (`src/csspin/cli.py`, function `cli`):

1. `find_spinfile` walks up from cwd to locate `spinfile.yaml`.
2. `load_minimal_tree` builds the tree from spin's own `schema.yaml`, merges
   in `spinfile.yaml`, then the optional user global
   (`$XDG_CONFIG_HOME/spin/global.yaml`, disable via
   `SPIN_DISABLE_GLOBAL_YAML`), then loads `csspin.builtin` and applies
   `plugins`/`plugin_paths`/`plugin_packages` directives.
3. For `provision`/`cleanup`/`system-provision`, control goes straight to
   `csspin.builtin` tasks (`src/csspin/builtin/__init__.py`), since plugin
   packages may not be installed yet.
4. Otherwise `load_plugins_into_tree` imports each declared plugin
   (`load_plugin` in `src/csspin/cli.py`, recursive over each plugin's
   `requires.spin` dependency list) and topologically sorts them
   (`reverse_toposort`) into `cfg.spin.topo_plugins` — dependencies configure
   and initialize before dependents.
5. `finalize_cfg_tree` runs every loaded plugin's `configure(cfg)` hook in
   topological order (`toporun`), then interpolates and type-sanitizes the
   whole tree (`tree.tree_sanitize`).
6. The click command group `commands` (built up by plugins calling `task()`)
   dispatches to the requested subcommand.

### Schemas and descriptors

Plugins optionally ship a `<plugin_name>_schema.yaml` next to their module,
declaring the type, default, and help text for each setting
(`src/csspin/schema.py`). Each schema node becomes a `BaseDescriptor`
subclass (`path`, `str`, `secret`, `int`, `float`, `bool`, `list`, `object`
— registered via `@descriptor(tag)` into `DESCRIPTOR_REGISTRY`), responsible
for coercing values and producing defaults. `secret`-typed values get
collected into `csspin.secrets` and are masked in all log output
(`obfuscate`). Spin's own top-level schema lives in `src/csspin/schema.yaml`.

### Plugin API surface

`src/csspin/__init__.py` is the public API plugins import from (`__all__`
lists the supported surface: `task`, `group`, `config`, `sh`, `echo`/`info`/
`debug`/`warn`/`error`, `interpolate`/`interpolate1`, `invoke`, `toporun`,
`Memoizer`, etc.). `src/csspin/cli.py` is spin's own bootstrap/CLI machinery
(click integration, plugin loading) and is imported lazily from `__init__.py`
functions to avoid an import cycle. `src/csspin/builtin/` holds the tasks
that are always available without any plugin packages (`provision`,
`cleanup`, `system-provision`, `run`, `schemadoc`, `distro`).

Key plugin-facing concepts:

- **`task()`**: decorator wrapping `click.command`, introspecting the
  function signature for special parameter names (`cfg` → config tree, `ctx`
  → click context, `args` → passthrough args) and `option()`/`argument()`
  annotations for the rest. `when="<hook>"` registers the task to run as part
  of `invoke(hook)` (e.g. how `csspin_python.pytest` hooks into `spin test`).
  `noenv=True` marks a task as runnable without a provisioned environment.
- **`invoke(hook, ...)`**: runs every task registered under a given hook name
  in registration order, filtering kwargs to what each task actually accepts
  — this is how workflow commands like `test`/`build`/`lint` (defined in
  `csspin_workflows.stdworkflows`) fan out to plugin-provided tasks.
- **`interpolate1`/`interpolate`**: `str.format_map`-style templating against
  the config tree plus `os.environ`, used pervasively (e.g. `"{python.version}"`,
  `"{spin.project_root}"`). Do not call at plugin module import time — the
  tree isn't populated yet; only call inside `configure()`/task bodies.
  Nearly every `csspin` I/O helper (`sh`, `cd`, `readtext`, ...) interpolates
  its path/string arguments automatically.
- **`sh()`**: the shell-out primitive. Runs inside `cfg.spin.subprocess_environment`
  (a context manager plugins like `csspin_python` replace to activate a venv)
  unless `use_subprocess_environment=False`.
- **`build_target`/`build_rules`**: a tiny make-like system driven by the
  `build_rules` section of `spinfile.yaml` (see the `doc/schemaref.rst` and
  `requirements.txt` rules in this repo's own `spinfile.yaml`), checking
  source mtimes via `is_up_to_date` before rebuilding.

### Tests

- `tests/test_*.py` — unit tests for the modules in `src/csspin/` (tree,
  schema, cli, yaml handling, public API).
- `tests/schema/` — schema-loading/coercion tests, including a standalone
  `testplugin` fixture package with its own `*_schema.yaml`.
  `tests/schema/test_schema_secrets.yaml` and friends cover the descriptor
  edge cases (secrets, internal-only overrides, environment coercion).
  `tests/schema/test_schema_extended.py` covers schema features not exercised
  by the YAML-file-driven tests.
- `tests/integration/` — exercises plugin loading and provisioning end to
  end (`test_provisioning.py`), and directive handling
  (`directives/test_directives.py`) against fixture plugins/spinfiles under
  `fixtures/`.
- `tests/data/csspin_dummy` and `tests/data/csspin_depend` — fake, installable
  plugin packages used to test plugin-package discovery/dependency loading
  without hitting a real index.
- Fixtures (`tests/conftest.py`) build config trees via `load_minimal_tree`
  (and `cfg`/`cfg_spin_dummy` for pre-built trees), rather than constructing
  `ConfigTree` objects by hand.

## Contribution workflow

See `CONTRIBUTING.md` for the full process (issue-first, draft MR/PR, GitLab
is canonical with a GitHub push mirror for external contributors). Release
notes go into `doc/relnotes.rst`; there is no separate changelog file.
