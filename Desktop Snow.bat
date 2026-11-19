@echo off
cd /d "%~dp0"
where python >nul 2>nul || (
  echo Python bulunamadi. https://www.python.org adresinden Python 3 kur ^(kurarken "Add to PATH" isaretle^).
  pause
  exit /b 1
)
python -c "import pygame, PIL" >nul 2>nul || (
  echo Ilk calistirma: gerekli paketler kuruluyor ^(pygame-ce, pillow^)...
  python -m pip install --user --disable-pip-version-check pygame-ce pillow || (pause & exit /b 1)
)
rem shortcut with the snow icon (recreated each run so it survives moving the folder)
powershell -NoProfile -Command "$py=(Get-Command pythonw).Source; $s=(New-Object -ComObject WScript.Shell).CreateShortcut('%~dp0Desktop Snow.lnk'); $s.TargetPath=$py; $s.Arguments=[char]34+'%~dp0desktop_snow.py'+[char]34; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0snow.ico'; $s.Description='Desktop Snow'; $s.Save()"
start "" pythonw "%~dp0desktop_snow.py" %*
