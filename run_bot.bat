@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title Discord Quest Service Bot v4.0 PRO

:: Kiểm tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy Python trên hệ thống!
    echo Vui lòng cài đặt Python và tích chọn "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

:: Chạy Discord Bot
python bot.py %*

if %errorlevel% neq 0 (
    echo.
    echo [THÔNG BÁO] Bot đã kết thúc với mã lỗi: %errorlevel%
    echo Hãy đảm bảo bạn đã điền bot_token trong config.json và chạy install.bat.
    echo.
    pause
)
