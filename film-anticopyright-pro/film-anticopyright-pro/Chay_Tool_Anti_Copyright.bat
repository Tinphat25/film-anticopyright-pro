@echo off
setlocal
title Film Anti-Copyright Pro
cd /d "%~dp0"
if exist "film-anticopyright-pro\run.py" (
    cd "film-anticopyright-pro"
)

echo ============================================================
echo   FILM ANTI-COPYRIGHT PRO - HE THONG KHANG BAN QUYEN AI
echo ============================================================
echo.
echo [OK] Dang khoi dong may chu ung dung...
echo.

python run.py

if errorlevel 1 (
    echo.
    echo [LOI] Co loi xay ra. Nhan phim bat ky de thoat.
    pause > nul
)
