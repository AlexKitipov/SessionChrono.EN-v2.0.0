@echo off
setlocal
cd /d "%~dp0"

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
python -m PyInstaller --clean --noconfirm sessionchrono.spec
if errorlevel 1 exit /b %errorlevel%

echo.
echo Build complete.
echo Generated output: dist\SessionChrono\
echo.
echo Do not commit build\, dist\, executables, shared libraries, bytecode, or other PyInstaller-generated artifacts.
