param(
    [string]$Provider = "",
    [string]$ProjectId = "",
    [string]$Location = "us",
    [switch]$SmokeTest,
    [Alias("h", "-help")]
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArguments = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($Help -or $AppArguments -contains "--help" -or $AppArguments -contains "-h") {
    @"
Usage: .\run.ps1 [options]

Starts the speech-to-text app with the local provider by default.

Options:
  -Provider <local|gcp|openai>  Override the transcription provider.
  -ProjectId <project-id>       Set the Google Cloud project for GCP mode.
  -Location <location>          Set the GCP location (default: us).
  -SmokeTest                    Validate setup without opening the app.
  -Help, -h, --help             Show this usage information and exit.
"@
    exit 0
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvRoot = Join-Path $scriptRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"
$createdVenv = $false

function Get-BootstrapPython {
    if ($env:PYTHON_EXE) {
        if (-not (Test-Path -LiteralPath $env:PYTHON_EXE)) {
            throw "PYTHON_EXE points to a missing file: $($env:PYTHON_EXE)"
        }

        return @{
            Path = $env:PYTHON_EXE
            Args = @()
        }
    }

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        return @{
            Path = $pyLauncher.Source
            Args = @("-3")
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and $pythonCommand.Source -notlike "*\WindowsApps\python.exe") {
        return @{
            Path = $pythonCommand.Source
            Args = @()
        }
    }

    throw (
        "Python 3.11+ was not found on PATH. Install Python and rerun .\run.ps1, " +
        "or set PYTHON_EXE to a Python executable path before launching the script."
    )
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    $bootstrapPython = Get-BootstrapPython
    Write-Host "Creating virtual environment in $venvRoot..."
    & $bootstrapPython.Path @($bootstrapPython.Args + @("-m", "venv", $venvRoot))
    $createdVenv = $true
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Virtual environment Python not found at $venvPython"
}

try {
    $previousErrorActionPreference = $ErrorActionPreference
    # Windows PowerShell 5.1 wraps native stderr as PowerShell error records.
    # The import probe is expected to fail on a fresh or incomplete environment,
    # so do not let ErrorActionPreference = "Stop" abort the repair path below.
    $ErrorActionPreference = "Continue"

    if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
        $previousNativeErrorPreference = $PSNativeCommandUseErrorActionPreference
        $PSNativeCommandUseErrorActionPreference = $false
    }

    & $venvPython -c "import faster_whisper; import speech_to_text_app" *> $null
    $packageInstalled = ($LASTEXITCODE -eq 0)
}
finally {
    $ErrorActionPreference = $previousErrorActionPreference

    if (Test-Path variable:previousNativeErrorPreference) {
        $PSNativeCommandUseErrorActionPreference = $previousNativeErrorPreference
    }
}

if ($createdVenv -or -not $packageInstalled) {
    try {
        $previousErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"

        & $venvPython -m pip --version *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Bootstrapping pip in the virtual environment..."
            & $venvPython -m ensurepip --upgrade
            $pipBootstrapExitCode = $LASTEXITCODE
        }
        else {
            $pipBootstrapExitCode = 0
        }

        if ($pipBootstrapExitCode -eq 0) {
            Write-Host "Installing project dependencies into the virtual environment..."
            & $venvPython -m pip install -e $scriptRoot
            $dependencyInstallExitCode = $LASTEXITCODE
        }
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($pipBootstrapExitCode -ne 0) {
        throw "Could not install pip into the virtual environment."
    }

    if ($dependencyInstallExitCode -ne 0) {
        throw "Project dependency installation failed."
    }
}

if (-not $Provider) {
    $Provider = "local"
}

$env:SPEECH_PROVIDER = $Provider
$env:GOOGLE_CLOUD_LOCATION = $Location

if ($ProjectId) {
    $env:GOOGLE_CLOUD_PROJECT = $ProjectId
}
else {
    $ProjectId = $env:GOOGLE_CLOUD_PROJECT
}

if ($SmokeTest) {
    Write-Output ("VIRTUAL_ENV=" + $venvRoot)
    Write-Output ("SPEECH_PROVIDER=" + $env:SPEECH_PROVIDER)
    Write-Output ("GOOGLE_CLOUD_PROJECT=" + $env:GOOGLE_CLOUD_PROJECT)
    Write-Output ("GOOGLE_CLOUD_LOCATION=" + $env:GOOGLE_CLOUD_LOCATION)
    & $venvPython -c "import sys; import speech_to_text_app; print(sys.executable)"
    exit $LASTEXITCODE
}

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
& $venvPython -m speech_to_text_app @AppArguments
