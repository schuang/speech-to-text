param(
    [string]$Provider = "",
    [string]$ProjectId = "",
    [string]$Location = "us",
    [switch]$SmokeTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvRoot = Join-Path $scriptRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"
$createdVenv = $false
$bootstrapPython = Get-BootstrapPython

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creating virtual environment in $venvRoot..."
    & $bootstrapPython.Path @($bootstrapPython.Args + @("-m", "venv", $venvRoot))
    $createdVenv = $true
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Virtual environment Python not found at $venvPython"
}

$stdoutPath = [System.IO.Path]::GetTempFileName()
$stderrPath = [System.IO.Path]::GetTempFileName()

try {
    $probe = Start-Process `
        -FilePath $venvPython `
        -ArgumentList @("-c", '"import speech_to_text_app"') `
        -NoNewWindow `
        -PassThru `
        -Wait `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath
    $packageInstalled = ($probe.ExitCode -eq 0)
}
finally {
    Remove-Item -LiteralPath $stdoutPath, $stderrPath -ErrorAction SilentlyContinue
}

if ($createdVenv -or -not $packageInstalled) {
    Write-Host "Installing project dependencies into the virtual environment..."
    & $venvPython -m pip install -e $scriptRoot
}

if (-not $Provider) {
    $Provider = $env:SPEECH_PROVIDER
}

if (-not $Provider) {
    $Provider = "gcp"
}

$env:SPEECH_PROVIDER = $Provider
$env:GOOGLE_CLOUD_PROJECT = $ProjectId
$env:GOOGLE_CLOUD_LOCATION = $Location

if ($SmokeTest) {
    Write-Output ("VIRTUAL_ENV=" + $venvRoot)
    Write-Output ("SPEECH_PROVIDER=" + $env:SPEECH_PROVIDER)
    Write-Output ("GOOGLE_CLOUD_PROJECT=" + $env:GOOGLE_CLOUD_PROJECT)
    Write-Output ("GOOGLE_CLOUD_LOCATION=" + $env:GOOGLE_CLOUD_LOCATION)
    Write-Output ("OLLAMA_BASE_URL=" + $env:OLLAMA_BASE_URL)
    Write-Output ("OLLAMA_MODEL=" + $env:OLLAMA_MODEL)
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
& $venvPython -m speech_to_text_app
