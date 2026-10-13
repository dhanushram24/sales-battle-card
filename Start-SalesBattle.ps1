param([int]$Port = 8000, [switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot
$backendDirectory = Join-Path $projectDirectory 'backend'
$pythonExecutable = Join-Path $backendDirectory 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw 'Create backend\venv and install backend\requirements.txt first. See README.md.'
}
if (-not $SkipBuild) {
    Push-Location (Join-Path $projectDirectory 'frontend')
    try {
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
}
Write-Host "Open http://localhost:$Port and keep this terminal open. Press Ctrl+C to stop."
Push-Location $backendDirectory
try {
    & $pythonExecutable -m uvicorn app.main:app --host 127.0.0.1 --port $Port --reload --no-proxy-headers
    if ($LASTEXITCODE -ne 0) { throw 'Backend stopped with an error. Check the terminal output above.' }
} finally { Pop-Location }
