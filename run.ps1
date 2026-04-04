param(
    [string]$Provider = "gcp",
    [string]$ProjectId = "",
    [string]$Location = "us",
    [switch]$SmokeTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$activateScript = Join-Path $scriptRoot ".venv\Scripts\Activate.ps1"

if (-not (Test-Path -LiteralPath $activateScript)) {
    throw "Virtual environment not found at $activateScript"
}

. $activateScript

$env:SPEECH_PROVIDER = $Provider

if ($Provider -eq "gcp" -and -not $ProjectId) {
    $ProjectId = $env:GOOGLE_CLOUD_PROJECT
}

if ($Provider -eq "gcp" -and -not $ProjectId) {
    throw (
        "Project ID is required. Set GOOGLE_CLOUD_PROJECT first, for example:`n`n" +
        '$env:GOOGLE_CLOUD_PROJECT="your-gcp-project-id"' +
        "`n.\\run.ps1`n`n" +
        "Or run with an explicit override:`n`n" +
        ".\\run.ps1 -ProjectId your-gcp-project-id"
    )
}

$env:GOOGLE_CLOUD_PROJECT = $ProjectId
$env:GOOGLE_CLOUD_LOCATION = $Location

if ($SmokeTest) {
    Write-Output ("VIRTUAL_ENV=" + $env:VIRTUAL_ENV)
    Write-Output ("SPEECH_PROVIDER=" + $env:SPEECH_PROVIDER)
    Write-Output ("GOOGLE_CLOUD_PROJECT=" + $env:GOOGLE_CLOUD_PROJECT)
    Write-Output ("GOOGLE_CLOUD_LOCATION=" + $env:GOOGLE_CLOUD_LOCATION)
    python -c "import sys; import speech_to_text_app; print(sys.executable)"
    exit $LASTEXITCODE
}

python -m speech_to_text_app
