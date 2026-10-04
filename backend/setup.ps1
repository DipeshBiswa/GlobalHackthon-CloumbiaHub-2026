$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ProjectDir ".venv"
$PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue

if (-not $PythonLauncher -and -not $PythonCommand) {
    throw "Python 3 was not found. Install Python, then run this script again."
}

if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
    if ($PythonLauncher) {
        & $PythonLauncher.Source -3 -m venv $VenvDir
    }
    else {
        & $PythonCommand.Source -m venv $VenvDir
    }
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $ProjectDir "requirements.txt")

Write-Host "Environment ready. Run .\download_model.ps1 while online, then .\run_offline.ps1."
