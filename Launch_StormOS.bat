@echo off
title StormOS Launcher
cd /d "%~dp0"
if exist "StormOS.exe" (
    start "" "StormOS.exe"
) else if exist "dist\StormOS.exe" (
    start "" "dist\StormOS.exe"
) else if exist "dist\StormOS\StormOS.exe" (
    start "" "dist\StormOS\StormOS.exe"
) else (
    python main.py
)
