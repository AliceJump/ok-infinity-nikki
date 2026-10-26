---
name: use-local-venv
description: Use repository-local uv environment for Python and test commands.
---

# uv / local venv

- Python 3.12 only; `pyproject.toml` and `uv.lock` are the authoritative dependency declarations.
- From the repository root: `uv sync --locked`, `uv run --locked python main.py` or `uv run --locked python main_debug.py`.
- Use `uv run --locked python -m compileall -q src main.py main_debug.py` and `uv run --locked python -m unittest discover -s tests -p 'TestProject*.py'` for portable checks.
- The historical `tests/TestMain.py` expects boilerplate game screenshots and is not in the automated smoke suite; migrate those assertions to Nikki fixtures before enabling it.
- `requirements.txt` is a *generated PyAppify release derivative*, not an editable dependency source. Update with `uv export --locked --no-dev --no-emit-project --no-hashes --no-annotate --output-file requirements.txt` after changing `pyproject.toml` and running `uv lock`. Commit both `uv.lock` and the generated requirements list.
- Avoid global Python or `pip install -r requirements.txt` for development. Release packaging may consume the generated file.
