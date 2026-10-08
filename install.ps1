<#
Registers the Chrome native messaging host, adds the widget to Windows startup, and starts it.

  powershell -ExecutionPolicy Bypass -File install.ps1 [-ExtensionDir <path>] [-ExtensionId <id>] [-Python <python.exe>]

-ExtensionDir defaults to the AI-Usage-Monitor folder next to this one.
Re-run after moving either folder: the unpacked extension's ID and the paths change.
#>
param(
    [string]$ExtensionDir = (Join-Path (Split-Path $PSScriptRoot -Parent) 'AI-Usage-Monitor'),
    [string]$ExtensionId,
    [string]$Python
)
$ErrorActionPreference = 'Stop'
$HostName = 'com.apc25.ai_usage_widget'
$DataDir = Join-Path $env:LOCALAPPDATA 'AIUsageWidget'
$WidgetDir = Join-Path $PSScriptRoot 'widget'
$HostScript = Join-Path $PSScriptRoot 'host\host.py'

# `python` can be a launcher stub that re-executes the real interpreter; resolve the real one.
if (-not $Python) { $Python = (& python -c "import sys; print(sys.executable)").Trim() }
& $Python -c "import PySide6"
if ($LASTEXITCODE -ne 0) { throw "PySide6 not importable from $Python. Pass -Python <path to python.exe>." }
$Pythonw = Join-Path (Split-Path $Python) 'pythonw.exe'

# An unpacked extension's ID is derived from its folder path; look it up in the Chrome profiles.
if (-not $ExtensionId) {
    $target = (Resolve-Path $ExtensionDir).Path.TrimEnd('\')
    foreach ($file in Get-ChildItem "$env:LOCALAPPDATA\Google\Chrome\User Data\*\Secure Preferences" -ErrorAction SilentlyContinue) {
        try { $settings = (Get-Content $file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json).extensions.settings } catch { continue }
        $match = $settings.PSObject.Properties | Where-Object { $_.Value.path -and $_.Value.path.TrimEnd('\') -eq $target }
        if ($match) { $ExtensionId = @($match)[0].Name; break }
    }
    if (-not $ExtensionId) { throw "Extension loaded from $target not found in Chrome. Pass -ExtensionId (see chrome://extensions)." }
}

New-Item -ItemType Directory -Force $DataDir | Out-Null

$bat = Join-Path $DataDir 'host.bat'
Set-Content -Path $bat -Encoding Default -Value "@echo off`r`n`"$Python`" -u `"$HostScript`" %*"

$manifestPath = Join-Path $DataDir 'native-host.json'
$manifest = [ordered]@{
    name            = $HostName
    description     = 'AI Usage Widget bridge'
    path            = $bat
    type            = 'stdio'
    allowed_origins = @("chrome-extension://$ExtensionId/")
}
[IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json), (New-Object Text.UTF8Encoding $false))

$key = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName"
New-Item -Path $key -Value $manifestPath -Force | Out-Null

$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut(
    (Join-Path ([Environment]::GetFolderPath('Startup')) 'AI Usage Widget.lnk'))
$shortcut.TargetPath = $Pythonw
$shortcut.Arguments = "`"$WidgetDir\main.py`""
$shortcut.WorkingDirectory = $WidgetDir
$shortcut.Save()

Start-Process -FilePath $Pythonw -ArgumentList "`"$WidgetDir\main.py`"" -WorkingDirectory $WidgetDir

Write-Host "Installed."
Write-Host "  extension id : $ExtensionId"
Write-Host "  python       : $Python"
Write-Host "  host manifest: $manifestPath"
Write-Host "  startup      : $($shortcut.FullName)"
Write-Host "Reload the extension in chrome://extensions so it connects to the widget."
