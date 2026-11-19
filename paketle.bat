@echo off
rem Desktop Snow klasorunu tasinabilir bir zip yapar: Desktop Snow.zip
cd /d "%~dp0"
del /q "Desktop Snow.zip" 2>nul
powershell -NoProfile -Command "$f='desktop_snow.py','ui.py','wallpaper.py','pet_art.py','art_hd.py','snow.ico','Desktop Snow.bat','paketle.bat','README.md'; if (Test-Path settings.json) { $f += 'settings.json' }; $t=Join-Path $env:TEMP 'DesktopSnowPack\Desktop Snow'; Remove-Item -Recurse -Force (Split-Path $t) -EA SilentlyContinue; New-Item -ItemType Directory -Force $t | Out-Null; Copy-Item $f $t; Compress-Archive -Path $t -DestinationPath 'Desktop Snow.zip' -Force; Remove-Item -Recurse -Force (Split-Path $t)"
echo Hazir: "%~dp0Desktop Snow.zip"
pause
