# Nikki Toolkit annotations

The source library lives in the `ok_templates` Git submodule. Open the parent project with ok-script Toolkit; `ok-script-toolkit.json` points the editor at that folder and publishes the runtime library to `assets/coco_annotations.json` and `assets/images/`, with the label enum at `src/data/FeatureList.py`.

The active templates are `dialog_icon`, `skip_choose` (W/S), `chat_icon`, and `skip_f`. The boxes follow the user's local annotations. `skip_b`, task-item handling and unused original atlas pages have been removed. The three screenshots remain because they supply active templates or real-scene replay fixtures. `assets/coco_detection.json` is a historical archive and is not loaded by the application.

Run `git submodule update --init --recursive` after checkout. Save source files using Toolkit, then explicitly publish runtime resources. Keep one annotation per template category. Before release, verify that the parent gitlink points to a commit available in the source repository.

`uv run --locked python scripts/verify_templates.py` checks IDs, image dimensions, bounds, and byte-exact source/runtime crops. `uv run --locked python -m unittest discover -s tests -p 'TestProject*.py' -v` covers actual template matching, normalized text-band measurement, independent choice memories, duplicate-click prevention and ignored task-item popups.

The locally authored W/S template is validated at native 3392×2400. At 2048×1450 and 1280×906 its resized score is below 0.9. These boxes and threshold are intentionally preserved; no claim of full-size support is made. Dialogue and chat icons pass the seven configured sizes. Live clicks and other dialogue scenes still require game validation.

Historical X-AnyLabeling work is preserved in the source repository's Git history at `592f0adf22abf7509ea88670a6a51b00d7f17a92`. New authoring uses Toolkit rather than the legacy conversion format.
