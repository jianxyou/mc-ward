# One-time setup on Windows: downloads Paper 26.3 + ViaVersion/ViaBackwards, unpacks the
# Hospital world, accepts the EULA and writes start_server.bat with the Java it found.
# Run from the mc-ward folder in PowerShell:
#   powershell -ExecutionPolicy Bypass -File server\setup_server.ps1
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # much faster downloads
Set-Location $PSScriptRoot

$PaperUrl        = 'https://fill-data.papermc.io/v1/objects/4208a692538104ec88699c0e078b2b89842920a10472ebb37e72cdda27c0d80e/paper-26.3-206.jar'
$ViaVersionUrl   = 'https://cdn.modrinth.com/data/P1OZGk5p/versions/qW2A0Ur2/ViaVersion-5.12.2-SNAPSHOT.jar'
$ViaBackwardsUrl = 'https://cdn.modrinth.com/data/NpvuJQoq/versions/Rq8nlm3i/ViaBackwards-5.12.2-SNAPSHOT.jar'

if (-not (Test-Path paper.jar)) { Write-Host 'downloading Paper 26.3 (55 MB)'; Invoke-WebRequest $PaperUrl -OutFile paper.jar }
New-Item -ItemType Directory -Force plugins | Out-Null
if (-not (Test-Path plugins\ViaVersion.jar))   { Write-Host 'downloading ViaVersion';   Invoke-WebRequest $ViaVersionUrl   -OutFile plugins\ViaVersion.jar }
if (-not (Test-Path plugins\ViaBackwards.jar)) { Write-Host 'downloading ViaBackwards'; Invoke-WebRequest $ViaBackwardsUrl -OutFile plugins\ViaBackwards.jar }
if (-not (Test-Path Hospital)) {
    Write-Host 'unpacking the Hospital world'
    Expand-Archive -Path Hospital.zip -DestinationPath . -Force
    Remove-Item -Force Hospital\session.lock -ErrorAction SilentlyContinue
}
Set-Content eula.txt 'eula=true'   # by running this you accept https://aka.ms/MinecraftEULA

# Java 25: the Minecraft launcher installs one when you have run version 26.3 once.
$LauncherJava = Join-Path $env:APPDATA '.minecraft\runtime\java-runtime-epsilon\windows-x64\java-runtime-epsilon\bin\java.exe'
if (Test-Path $LauncherJava) {
    $Java = $LauncherJava
} elseif (Get-Command java -ErrorAction SilentlyContinue) {
    $Java = (Get-Command java).Source
} else {
    Write-Host 'No Java found. Run Minecraft 26.3 once from the launcher, or install Temurin 25 from https://adoptium.net, then run this script again.'
    exit 1
}
$Version = (& $Java -version 2>&1 | Select-Object -First 1)
Write-Host "using Java: $Java"
Write-Host "            $Version"
if ($Version -notmatch '"25') { Write-Host 'WARNING: this does not look like Java 25; Paper 26.3 needs Java 25.' }

@"
@echo off
cd /d "%~dp0"
"$Java" -Xms1G -Xmx4G -jar paper.jar nogui
pause
"@ | Set-Content start_server.bat -Encoding ASCII

Write-Host 'done. Start the server with: server\start_server.bat'
