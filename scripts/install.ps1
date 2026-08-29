# Install Lobesync without requiring an activated Python environment.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Version = $env:LOBESYNC_VERSION

if ($Version -and $Version -notmatch "^[0-9A-Za-z._-]+$") {
    throw "LOBESYNC_VERSION must be a version such as 1.0.0."
}

function Find-Uv {
    $uvCommand = Get-Command uv -ErrorAction SilentlyContinue
    if ($uvCommand) {
        return $uvCommand.Source
    }

    $uvPath = Join-Path $HOME ".local\bin\uv.exe"
    if (Test-Path $uvPath) {
        return $uvPath
    }

    return $null
}

$uv = Find-Uv
if (-not $uv) {
    Write-Host "Installing uv, the isolated Python tool manager..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $uv = Find-Uv
}

if (-not $uv) {
    throw "uv was installed but could not be found. Open a new PowerShell window and try again."
}

$package = "lobesync"
$displayVersion = "the latest release"
if ($Version) {
    $package = "lobesync==$Version"
    $displayVersion = $Version
}

Write-Host "Installing Lobesync $displayVersion with Python 3.13..."
& $uv tool install --python 3.13 $package
if ($LASTEXITCODE -ne 0) {
    throw "Lobesync installation failed."
}

& $uv tool update-shell
if ($LASTEXITCODE -ne 0) {
    throw "Lobesync was installed, but its command directory could not be added to PATH."
}

$toolBin = (& $uv tool dir --bin).Trim()
Write-Host ""
Write-Host "Lobesync $displayVersion is installed."
Write-Host "Open a new PowerShell window, then run: lobesync"
Write-Host "Installed command directory: $toolBin"
