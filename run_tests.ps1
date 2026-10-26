param(
    [switch]$LegacyImageTests
)

$ErrorActionPreference = "Stop"
uv sync --locked
if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }

uv run --locked python -m compileall -q src main.py main_debug.py
if ($LASTEXITCODE -ne 0) { throw "Python compilation failed" }

uv run --locked python -m unittest discover -s tests -p "TestProject*.py" -v
if ($LASTEXITCODE -ne 0) { throw "Project smoke tests failed" }

if ($LegacyImageTests) {
    uv run --locked python -m unittest discover -s tests -p "TestMain.py" -v
    if ($LASTEXITCODE -ne 0) { throw "Legacy image tests failed" }
}
