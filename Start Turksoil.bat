@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_turksoil.ps1"
if errorlevel 1 (
  echo.
  echo Turksoil could not start. Review the error above.
  pause
)
