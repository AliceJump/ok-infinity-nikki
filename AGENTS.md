# Project workflow

Read the matching skill before changing code, committing, or handling a PR:

- `.agents/skills/repository-workflow/SKILL.md`: repository changes, scope, validation and pull requests.
- `.agents/skills/use-local-venv/SKILL.md`: Python, uv and tests.

`ok-infinity-nikki` follows the basic layout of `ok-end-field`, but does not reuse game-specific assets or runtime logic. Prefer a focused PR for each independently deployable change. Do not push directly to `main`.

The `x-anylabeling-asset` directory is source annotation data, not the application runtime assets. Keep it intact until a separate `ok-infinity-nikki-x-anylabeling-asset` repository has been created and fully populated; then migrate it into a real Git submodule in its own PR.
