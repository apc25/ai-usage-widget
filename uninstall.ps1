<#
Stops the widget and removes everything install.ps1 registered. settings.json and usage.json are kept.

  powershell -ExecutionPolicy Bypass -File uninstall.ps1
#>
$ErrorActionPreference = 'Stop'
$HostName = 'com.apc25.ai_usage_widget'
$DataDir = Join-Path $env:LOCALAPPDATA 'AIUsageWidget'
$WidgetScript = Join-Path $PSScriptRoot 'widget\main.py'

Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*$WidgetScript*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Confirm:$false }

Remove-Item "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName" -ErrorAction SilentlyContinue
Remove-Item (Join-Path ([Environment]::GetFolderPath('Startup')) 'AI Usage Widget.lnk') -ErrorAction SilentlyContinue
Remove-Item (Join-Path $DataDir 'host.bat'), (Join-Path $DataDir 'native-host.json') -ErrorAction SilentlyContinue

Write-Host "Uninstalled. Kept settings in $DataDir"
