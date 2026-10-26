# Development guide

## Repository structure

- `main.py` / `main_debug.py` — application entry points.
- `src/config.py` — ok-script configuration, task registry and capture/OCR settings.
- `src/tasks/` — Nikki task implementations; `src/interaction/` — Windows interaction helpers.
- `src/image/` — image processing; `src/data/` — data and feature definitions.
- `assets/` — runtime templates, COCO metadata and other packaged assets.
- `x-anylabeling-asset/` — original annotation project; will move to a dedicated repository/submodule.
- `tests/` — tests, with separate legacy image fixtures.
- `i18n/` — localizations.
- `.github/workflows/` — CI and release build.

## Source checkout

Requires Windows 10/11, Python 3.12 and [uv](https://docs.astral.sh/uv/).

```pwsh
git clone --recurse-submodules https://github.com/AliceJump/ok-infinity-nikki.git
cd ok-infinity-nikki
uv sync --locked
uv run --locked python main.py
# or: uv run --locked python main_debug.py
```

The `uv.lock` file pins the entire environment. Do not edit generated
`requirements.txt` by hand. Regenerate it with:

```pwsh
uv lock
uv export --locked --no-dev --no-emit-project --no-hashes --no-annotate --output-file requirements.txt
```

## Tests and releases

```pwsh
.\run_tests.ps1
uv run --locked python -m compileall -q src main.py main_debug.py
```

The original `TestMain.py` is a boilerplate screenshot test and is excluded
until it has real Infinity Nikki fixtures. Enable explicitly with
`./run_tests.ps1 -LegacyImageTests`.

Tags `v*` trigger `build.yml`, which verifies locked dependencies, builds
using PyAppify and creates a GitHub release. Before tagging, confirm
`pyappify.yml`, `deploy.txt`, `uv.lock` and generated `requirements.txt`
match the intended release.

## Separating annotations into a submodule

Create a public repository **AliceJump/ok-infinity-nikki-x-anylabeling-asset**
before trying the split. Commit the exact existing
`x-anylabeling-asset/` contents (including large PNG/JSON files; use Git LFS
if necessary) to that repository, then replace the parent folder with a
Git submodule pinned to the reviewed asset commit, with a matching
`.gitmodules` entry. Do **not** remove the parent copy until the
new repository and its Git LFS data have been verified. Runtime `assets/`
should stay in the parent application unless intentionally migrated later.
