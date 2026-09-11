@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title AutoQuest Bot Controller v4.0 PRO

:: Khởi chạy giao diện điều khiển GUI
start "" pythonw gui.py
if %errorlevel% neq 0 (
    python gui.py
)
