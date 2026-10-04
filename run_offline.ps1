$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Uvicorn = Join-Path $ProjectDir ".venv\Scripts\uvicorn.exe"

if (-not (Test-Path $Uvicorn)) {
    throw "No .venv found. Run .\setup.ps1 first."
}

$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"

& $Uvicorn --app-dir $ProjectDir api:app --host 127.0.0.1 --port 8000
