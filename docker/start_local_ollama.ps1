<#
.SYNOPSIS
    Starts local Ollama with qwen2.5:3b and nomic-embed-text and exposes it via Cloudflare Quick Tunnel.
.DESCRIPTION
    Supports the LogisticsRAGAgent Hybrid Architecture (HF Spaces n8n + Qdrant Cloud + Local Windows Ollama).
#>

[CmdletBinding()]
param(
    [string]$OllamaUrl = "http://127.0.0.1:11434",
    [string[]]$RequiredModels = @("qwen2.5:3b", "nomic-embed-text")
)

$ErrorActionPreference = "Stop"

# Ensure sufficient context window for multi-tool RAG + Gmail aggregation on 4 GB VRAM GPUs
if (-not $env:OLLAMA_CONTEXT_LENGTH) {
    $env:OLLAMA_CONTEXT_LENGTH = "8192"
}

Write-Host "=== LogisticsRAGAgent: Local Ollama + Cloudflare Tunnel ===" -ForegroundColor Cyan
Write-Host "Using OLLAMA_CONTEXT_LENGTH=$($env:OLLAMA_CONTEXT_LENGTH)" -ForegroundColor DarkCyan

# 1. Verify Ollama CLI
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaCmd) {
    $fallbackOllama = Join-Path $env:LocalAppData "Programs\Ollama\ollama.exe"
    if (Test-Path $fallbackOllama) {
        $env:Path += ";" + (Split-Path $fallbackOllama -Parent)
        $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    }
}
if (-not $ollamaCmd) {
    Write-Error "Ollama CLI was not found. Install it via: winget install Ollama.Ollama"
    exit 1
}

# 2. Check / start Ollama server
function Test-OllamaApi {
    try {
        $resp = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -Method Get -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-OllamaApi)) {
    Write-Host "[1/3] Starting 'ollama serve' in background..." -ForegroundColor Yellow
    Start-Process -FilePath $ollamaCmd.Source -ArgumentList "serve" -WindowStyle Minimized
    $ready = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1.5
        if (Test-OllamaApi) {
            $ready = $true
            break
        }
    }
    if (-not $ready) {
        Write-Error "Ollama API did not respond at $OllamaUrl after starting 'ollama serve'."
        exit 1
    }
}
Write-Host "[1/3] Ollama API is running at $OllamaUrl" -ForegroundColor Green

# 3. Verify and pull required models
$tags = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -Method Get -TimeoutSec 10
$installedNames = @()
if ($tags.models) {
    $installedNames = $tags.models | ForEach-Object { $_.name }
}

Write-Host "[2/3] Checking required models ($($RequiredModels -join ', '))..." -ForegroundColor Yellow
foreach ($model in $RequiredModels) {
    $hasModel = $installedNames | Where-Object { $_ -eq $model -or $_ -like "${model}:*" }
    if (-not $hasModel) {
        Write-Host "Pulling model '$model'..." -ForegroundColor Cyan
        & $ollamaCmd.Source pull $model
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to pull model '$model'."
            exit 1
        }
    } else {
        Write-Host "  - Model '$model' is ready." -ForegroundColor Green
    }
}

# 4. Verify cloudflared and launch tunnel
$cfCmd = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cfCmd) {
    Write-Error "cloudflared CLI was not found. Install it via: winget install Cloudflare.cloudflared"
    exit 1
}

Write-Host "[3/3] Starting Cloudflare Quick Tunnel to $OllamaUrl ..." -ForegroundColor Yellow
Write-Host "When the https://*.trycloudflare.com URL appears below:" -ForegroundColor Cyan
Write-Host "  1) Copy that HTTPS URL into Hugging Face Space variable OLLAMA_BASE_URL" -ForegroundColor Cyan
Write-Host "  2) Update your Ollama credential Base URL inside n8n" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the tunnel." -ForegroundColor DarkGray

$urlShown = $false
& $cfCmd.Source tunnel --url http://localhost:11434 2>&1 | ForEach-Object {
    $line = "$_"
    Write-Host $line
    if (-not $urlShown -and $line -match "(https://[a-zA-Z0-9-]+\.trycloudflare\.com)") {
        $urlShown = $true
        $tunnelUrl = $Matches[1]
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Green
        Write-Host "  OLLAMA_BASE_URL = $tunnelUrl" -ForegroundColor Green
        Write-Host "  Paste this URL into HF Spaces Secrets/Variables and n8n!" -ForegroundColor Green
        Write-Host "============================================================" -ForegroundColor Green
        Write-Host ""
    }
}
