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

The working files are `ok_templates/coco_annotations.json` (Template), `ok_templates/boxes.json` (Rect) and `ok_templates/points.json` (Point). The Rect and Point files initially contain empty COCO tables. The two `screenshot_20261026_*.png` files are real 3392×2400 choice scenes; `184825` supplies the history icon and W/S template, and `184802` supplies a second background for replay validation. Keep one annotation per category to satisfy the runtime loader.

## Publishing

Toolkit's **save annotation** updates source files in the `ok_templates` submodule only. Explicitly use Toolkit's **Publish** action to regenerate `assets/coco_annotations.json`, `assets/images/` and, when selected, `src/data/FeatureList.py`. Before committing, check the published output, code references and feature tests. Publishing Position is separate and requires a runtime loader before any `self.pos` references can be used; the plugin alone does not enable it in the game.

The original application used `assets/coco_detection.json`, retained as a historical archive. The active library is `assets/coco_annotations.json`; its history icon, W/S hint, and new `chat_icon` follow the local Toolkit annotations on the native-resolution screenshot. Ordinary dialogue F, B, and task-marker templates retain their original crops. The five original feature names stay unchanged, with `chat_icon` added to count actual dialogue options. Matching uses each annotation's own anchored coordinates instead of the old 1920×1080 search box.

Run `uv run --locked python scripts/verify_templates.py` to check IDs, dimensions, bounds, and exact source/runtime crop equality. `uv run --locked python -m unittest discover -s tests -p 'TestProjectTemplates.py' -v` replays the history and chat-option icons in both screenshots at all seven configured sizes using the installed matcher at threshold 0.9, and checks task actions with game input mocked. The locally authored W/S crop is checked at native 3392×2400; its resized matches at 2048×1450 and 1280×906 are below 0.9, so it must not gate the new chat-option selector. These are resized screenshot checks; other dialogue states and live rendering still require game validation.

The original X-AnyLabeling PNG/JSON work (16 files, 53.7 MB) is preserved in the **asset repository's Git history** (commit `592f0adf22abf7509ea88670a6a51b00d7f17a92`) and no longer appears in the parent working tree. New screenshots and edits should use Toolkit, not the old conversion script.
