# Development guide

## Repository structure

- `main.py` / `main_debug.py` — application entry points.
- `src/config.py` — ok-script configuration, task registry and capture/OCR settings.
- `src/tasks/` — Nikki task implementations; `src/interaction/` — Windows interaction helpers.
- `src/image/` — image processing; `src/data/` — data and feature definitions.
- `assets/` — runtime templates, COCO metadata and other packaged assets.
- `ok_templates/` — independently managed Toolkit Template/Rect/Point authoring submodule (added by the Toolkit layout PR).
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

## Toolkit authoring source (independent migration)

The annotation source uses `ok_templates/` as a Git submodule and
`ok-script-toolkit.json` at the project root; see the independent
[Toolkit layout PR](https://github.com/AliceJump/ok-infinity-nikki/pull/2).

- `ok_templates/coco_annotations.json`, `boxes.json`, and `points.json`
  hold editable Template / Rect / Point annotations (COCO tables).
- `assets/coco_annotations.json` plus `assets/images/` hold the published,
  runtime-consumed template library.
- Saving a working annotation does **not** publish it, and the game will not
  load new Position resources without a project-specific loader.
- The historical X-AnyLabeling source lives in the asset repository history
  and is no longer the supported editing workflow.

Do not include the authoring submodule in release `deploy.txt` or move old
unverified annotation files into a live runtime directory.
