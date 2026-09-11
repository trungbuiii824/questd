@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title Discord Quest Auto-Completer v4.0 PRO


:: Kiểm tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy Python trên hệ thống!
    echo Vui lòng cài đặt Python và tích chọn "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

:: Kiểm tra nếu tokens.txt chưa tồn tại thì tạo file mẫu
if not exist "tokens.txt" (
    if exist "tokens.example.txt" (
        copy tokens.example.txt tokens.txt >nul
    ) else (
        echo # Dán Discord Token vào đây (mỗi dòng 1 token) > tokens.txt
    )
)

:: Chạy chương trình chính
python main.py %*

if %errorlevel% neq 0 (
    echo.
    echo [THÔNG BÁO] Chương trình đã kết thúc với mã lỗi: %errorlevel%
    echo Nếu lỗi thiếu thư viện, hãy chạy file install.bat trước.
    echo.
    pause
)
