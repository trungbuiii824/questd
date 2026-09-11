@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title Discord Quest Auto-Completer - Cài đặt Thư Viện


echo ======================================================================
echo    CÀI ĐẶT THƯ VIỆN CHO DISCORD QUEST AUTO-COMPLETER v4.0 PRO
echo ======================================================================
echo.

:: Kiểm tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy Python trên máy tính của bạn!
    echo Vui lòng cài đặt Python (phiên bản 3.9 trở lên) và nhớ tích chọn
    echo "Add Python to PATH" trong lúc cài đặt.
    echo Tải Python tại: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [*] Đang kiểm tra và cài đặt các thư viện từ requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [LỖI] Cài đặt thư viện thất bại! Vui lòng kiểm tra lại kết nối mạng.
    echo.
    pause
    exit /b 1
)

:: Khởi tạo file cấu hình nếu chưa có
if not exist "config.json" (
    if exist "config.example.json" (
        echo [*] Đang tạo file config.json từ mẫu...
        copy config.example.json config.json >nul
    )
)

:: Khởi tạo file tokens.txt nếu chưa có
if not exist "tokens.txt" (
    echo [*] Đang tạo file tokens.txt...
    echo # Dán Discord Token của bạn vào đây (mỗi dòng 1 token) > tokens.txt
)

echo.
echo ======================================================================
echo [THÀNH CÔNG] Đã cài đặt xong toàn bộ thư viện cần thiết!
echo Bây giờ bạn có thể:
echo   1. Mở file tokens.txt và dán Discord Token của bạn vào đó.
echo   2. Mở file config.json để tùy chỉnh Webhook, thời gian quét...
echo   3. Nhấp đúp vào run.bat để chạy CLI, hoặc run_bot.bat để chạy Discord Bot!
echo ======================================================================
echo.
pause
