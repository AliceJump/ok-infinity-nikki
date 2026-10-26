# ok-script Toolkit templates (Nikki)

Nikki uses the current [ok-script Toolkit authoring format](https://github.com/AliceJump/ok-script-toolkit/blob/main/docs/box-resources.md), not X-AnyLabeling. The working template source is a Git submodule at `ok_templates/`, pinned to [ok-infinity-nikki-x-anylabeling-asset](https://github.com/AliceJump/ok-infinity-nikki-x-anylabeling-asset). The old repository name reflects its historical origin; it is not the working format.

## Checkout

```powershell
git clone --recurse-submodules https://github.com/AliceJump/ok-infinity-nikki.git
cd ok-infinity-nikki
# In an existing clone:
git submodule sync --recursive
git submodule update --init --recursive
```

Open the parent project in VS Code or JetBrains and install ok-script Toolkit. It reads the root `ok-script-toolkit.json` with these project facts:

- `templates.directory = "ok_templates"`: editable PNGs and three COCO files
- `labelEnum.path = "src/data/FeatureList"`, `name = "FeatureList"`: existing imports stay valid
- `templates.cocoAnnotations = "assets/coco_annotations.json"`: the actual **runtime** library

The working files are `ok_templates/coco_annotations.json` (Template), `ok_templates/boxes.json` (Rect) and `ok_templates/points.json` (Point). The Rect and Point files initially contain empty COCO tables.

## Publishing

Toolkit's **save annotation** updates source files in the `ok_templates` submodule only. Explicitly use Toolkit's **Publish** action to regenerate `assets/coco_annotations.json`, `assets/images/` and, when selected, `src/data/FeatureList.py`. Before committing, check the published output, code references and feature tests. Publishing Position is separate and requires a runtime loader before any `self.pos` references can be used; the plugin alone does not enable it in the game.

The original application used `assets/coco_detection.json`. This PR adds a byte-identical `assets/coco_annotations.json`, updates the runtime path and **retains the old file as a compatibility archive**. The existing 5 template categories and boxes are unchanged; the source submodule has converted, deduplicated working COCO metadata.

The original X-AnyLabeling PNG/JSON work (16 files, 53.7 MB) is preserved in the **asset repository's Git history** (commit `592f0adf22abf7509ea88670a6a51b00d7f17a92`) and no longer appears in the parent working tree. New screenshots and edits should use Toolkit, not the old conversion script.
