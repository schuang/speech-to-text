param(
    [string]$Provider = "",
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

if (-not $Provider) {
    $Provider = $env:SPEECH_PROVIDER
}

if (-not $Provider) {
    $Provider = "gcp"
}

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

if ($Provider -eq "ollama" -and -not $env:OLLAMA_BASE_URL) {
    throw (
        "OLLAMA_BASE_URL is required for Ollama mode. Set it first, for example:`n`n" +
        '$env:SPEECH_PROVIDER="ollama"' +
        "`n" +
        '$env:OLLAMA_BASE_URL="http://your-ollama-host:11434"' +
        "`n" +
        '$env:OLLAMA_MODEL="gemma4:default"' +
        "`n.\\run.ps1"
    )
}

$env:GOOGLE_CLOUD_PROJECT = $ProjectId
$env:GOOGLE_CLOUD_LOCATION = $Location

if ($SmokeTest) {
    Write-Output ("VIRTUAL_ENV=" + $env:VIRTUAL_ENV)
    Write-Output ("SPEECH_PROVIDER=" + $env:SPEECH_PROVIDER)
    Write-Output ("GOOGLE_CLOUD_PROJECT=" + $env:GOOGLE_CLOUD_PROJECT)
    Write-Output ("GOOGLE_CLOUD_LOCATION=" + $env:GOOGLE_CLOUD_LOCATION)
    Write-Output ("OLLAMA_BASE_URL=" + $env:OLLAMA_BASE_URL)
    Write-Output ("OLLAMA_MODEL=" + $env:OLLAMA_MODEL)
    python -c "import sys; import speech_to_text_app; print(sys.executable)"
    exit $LASTEXITCODE
}

python -m speech_to_text_app
