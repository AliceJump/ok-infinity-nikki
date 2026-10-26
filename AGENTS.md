# Project workflow

Read the matching skill before changing code, committing, or handling a PR:

- `.agents/skills/repository-workflow/SKILL.md`: repository changes, scope, validation and pull requests.
- `.agents/skills/use-local-venv/SKILL.md`: Python, uv and tests.

`ok-infinity-nikki` follows the basic layout of `ok-end-field`, but does not reuse game-specific assets or runtime logic. Prefer a focused PR for each independently deployable change. Do not push directly to `main`.

The application uses a Toolkit-managed `ok_templates` source repository as a submodule, separate from runtime `assets`. This independent change is tracked in the Toolkit layout PR. Do not reintroduce legacy X-AnyLabeling working files, do not edit the game runtime COCO without a dedicated change, and verify every gitlink SHA before release.
