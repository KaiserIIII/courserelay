@echo off
setlocal
cd /d "%~dp0"
python -X utf8 -m courserelay serve
if errorlevel 1 pause
