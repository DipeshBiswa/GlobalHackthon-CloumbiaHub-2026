$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw "No .venv found. Run .\setup.ps1 first."
}

& $VenvPython (Join-Path $ProjectDir "download_insight_model.py")
