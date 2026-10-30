# Nikki Toolkit annotations

The source library lives in the `ok_templates` Git submodule. Open the parent project with ok-script Toolkit; `ok-script-toolkit.json` points the editor at that folder and publishes runtime resources to `assets/coco_annotations.json` and `assets/images/`, with the label enum at `src/data/FeatureList.py`.

## Authoring and publishing

Run `git submodule update --init --recursive` when working on source annotations. Save source files using Toolkit, then explicitly publish runtime resources. Saving source annotations alone does not publish changes to the application. Preserve the authored screenshots, annotations and published resources; commit source changes before updating the parent's gitlink.

`assets/coco_detection.json` is a historical archive and is not loaded by the application. Historical X-AnyLabeling work remains available in the source repository's Git history at `592f0adf22abf7509ea88670a6a51b00d7f17a92`.

## Test scope

Template screenshots and annotation data are authoring inputs, not a separate CI test suite. There is no template-validation workflow, fixed category or annotation-count gate, source/runtime pixel-equality check, or screenshot-specific replay suite. Do not reintroduce these checks as prerequisites for template edits.

The application's PR Test compiles the code and runs the remaining `TestProject*.py` functional tests against published runtime resources. It does not initialize the annotation-source submodule. Keep tests focused on task behavior, state transitions, input guards, configuration and framework integration. Actual recognition behavior still needs observation in the game.
