<#
.SYNOPSIS
    Builds standalone LogisticsRAGAgent.exe using PyInstaller.
#>
[CmdletBinding()]
param(
    [switch]$SkipPipInstall
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=== LogisticsRAGAgent PyInstaller Build ===" -ForegroundColor Cyan
Write-Host "Working directory: $ScriptDir"

if (-not $SkipPipInstall) {
    Write-Host "Checking/installing requirements.txt..." -ForegroundColor Yellow
    python -m pip install -r (Join-Path $ScriptDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed with exit code $LASTEXITCODE"
    }
}

foreach ($dir in @("build", "dist")) {
    $target = Join-Path $ScriptDir $dir
    if (Test-Path $target) {
        Remove-Item -Recurse -Force $target
    }
}
$specFile = Join-Path $ScriptDir "LogisticsRAGAgent.spec"
if (Test-Path $specFile) {
    Remove-Item -Force $specFile
}

Write-Host "Running PyInstaller..." -ForegroundColor Yellow
python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "LogisticsRAGAgent" `
    --collect-all "customtkinter" `
    --hidden-import "i18n" `
    --hidden-import "config_manager" `
    --hidden-import "api_client" `
    (Join-Path $ScriptDir "main.py")

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$ExePath = Join-Path $ScriptDir "dist\LogisticsRAGAgent.exe"
if (-not (Test-Path $ExePath)) {
    throw "Expected output executable not found at $ExePath"
}

$SizeMB = [math]::Round((Get-Item $ExePath).Length / 1MB, 2)
Write-Host "Build succeeded: $ExePath ($SizeMB MB)" -ForegroundColor Green