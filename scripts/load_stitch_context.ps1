# OvelhaInvest — Load Stitch Design Context
# Fetches all screen designs from Google Stitch into design/screens/
# Requires: STITCH_API_KEY env var set
#
# Usage:
#   $env:STITCH_API_KEY = "your-key-here"
#   .\scripts\load_stitch_context.ps1

param(
    [string]$ProjectId = "11580419759191253062",
    [string]$OutputDir = "design\screens"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Set-Location $Root

# ── Validate API key ──────────────────────────────────────────────────────────
if (-not $env:STITCH_API_KEY) {
    Write-Host ""
    Write-Host "ERROR: STITCH_API_KEY is not set." -ForegroundColor Red
    Write-Host ""
    Write-Host "To get an API key:"
    Write-Host "  1. Open https://stitch.withgoogle.com/u/1/settings"
    Write-Host "  2. Go to 'API Keys' section"
    Write-Host "  3. Generate a new key and copy it"
    Write-Host ""
    Write-Host "Then run:"
    Write-Host "  `$env:STITCH_API_KEY = 'your-key-here'"
    Write-Host "  .\scripts\load_stitch_context.ps1"
    Write-Host ""
    exit 1
}

# ── Ensure output dir exists ──────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Write-Host "Output: $OutputDir" -ForegroundColor Cyan

# ── List screens ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Fetching screen list for project $ProjectId ..." -ForegroundColor Yellow

$screensJson = npx @_davideast/stitch-mcp tool list_screens `
    -d "{""projectId"": ""$ProjectId""}" `
    -o json 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to list screens. Check your API key and project ID." -ForegroundColor Red
    Write-Host $screensJson
    exit 1
}

$screens = $screensJson | ConvertFrom-Json
Write-Host "Found $($screens.Count) screens" -ForegroundColor Green

# ── Fetch each screen ─────────────────────────────────────────────────────────
foreach ($screen in $screens) {
    $screenId = $screen.id
    $screenName = $screen.name -replace '[^a-zA-Z0-9_-]', '_'
    Write-Host ""
    Write-Host "  Fetching: $($screen.name) ($screenId) ..." -ForegroundColor Cyan

    # HTML code
    $html = npx @_davideast/stitch-mcp tool get_screen_code `
        -d "{""projectId"": ""$ProjectId"", ""screenId"": ""$screenId""}" `
        -o raw 2>&1

    if ($html -and $html.Length -gt 0) {
        $htmlPath = Join-Path $OutputDir "$screenName.html"
        $html | Set-Content -Path $htmlPath -Encoding UTF8
        Write-Host "    HTML: $htmlPath" -ForegroundColor Green
    }

    # PNG screenshot
    $imgData = npx @_davideast/stitch-mcp tool get_screen_image `
        -d "{""projectId"": ""$ProjectId"", ""screenId"": ""$screenId""}" `
        -o raw 2>&1

    if ($imgData -and $imgData.Length -gt 0) {
        $pngPath = Join-Path $OutputDir "$screenName.png"
        # imgData is base64 — decode and write
        $bytes = [Convert]::FromBase64String($imgData)
        [IO.File]::WriteAllBytes((Join-Path $Root $pngPath), $bytes)
        Write-Host "    PNG: $pngPath" -ForegroundColor Green
    }
}

# ── Generate DESIGN.md ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Generating design/DESIGN.md ..." -ForegroundColor Yellow

$mdLines = @(
    "# OvelhaInvest — Stitch Design Reference",
    "",
    "**Stitch Project ID:** ``$ProjectId``",
    "**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm')",
    "",
    "## Screens",
    ""
)

foreach ($screen in $screens) {
    $screenName = $screen.name -replace '[^a-zA-Z0-9_-]', '_'
    $mdLines += "### $($screen.name)"
    $mdLines += ""
    $mdLines += "- **Screen ID:** ``$($screen.id)``"
    $mdLines += "- **HTML:** [screens/$screenName.html](screens/$screenName.html)"
    $mdLines += "- **PNG:** [screens/$screenName.png](screens/$screenName.png)"
    $mdLines += ""
}

$mdLines | Set-Content -Path "design\DESIGN.md" -Encoding UTF8
Write-Host "design/DESIGN.md written" -ForegroundColor Green

Write-Host ""
Write-Host "Done. All screens saved to $OutputDir/" -ForegroundColor Green
Write-Host "Commit with: git add design/ && git commit -m 'chore: sync stitch design context'"
