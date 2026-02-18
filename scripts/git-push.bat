@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

:: ============================================================
::  git-push.bat — Generic Git Sync Tool (Windows)
::  Chức năng: Add → Commit → Pull (rebase) → Push → Tag
::  Cách dùng: git-push.bat ["commit message"]
::  Để dùng cho dự án khác: copy file này vào thư mục gốc
::  của dự án rồi double-click hoặc chạy từ CMD/PowerShell.
:: ============================================================

:: ============================================================
:: 0. Kiểm tra thư mục Git
:: ============================================================
if not exist ".git" (
    echo [ERROR] Day khong phai la thu muc Git!
    echo    ^> Chay 'git init' de khoi tao, hoac di chuyen den dung thu muc.
    pause
    exit /b 1
)

:: ============================================================
:: 1. Lấy tên nhánh hiện tại
:: ============================================================
for /f "tokens=*" %%b in ('git branch --show-current 2^>nul') do set "CURRENT_BRANCH=%%b"
if "%CURRENT_BRANCH%"=="" (
    echo [ERROR] Khong xac dinh duoc nhanh hien tai.
    echo    ^> Co the repo dang o trang thai detached HEAD.
    pause
    exit /b 1
)
echo [INFO] Nhanh hien tai: %CURRENT_BRANCH%

:: ============================================================
:: 2. Kiểm tra remote origin
:: ============================================================
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Chua co remote 'origin'. Vui long them remote truoc:
    echo    ^> git remote add origin ^<URL^>
    pause
    exit /b 1
)
for /f "tokens=*" %%r in ('git remote get-url origin') do set "REMOTE_URL=%%r"
echo [INFO] Remote: %REMOTE_URL%

:: ============================================================
:: 3. Nhập commit message
:: ============================================================
set "COMMIT_MSG=%~1"
if "%COMMIT_MSG%"=="" (
    echo.
    set /p "COMMIT_MSG=Commit message (Enter de dung mac dinh): "
)

if "%COMMIT_MSG%"=="" (
    set "COMMIT_MSG=chore: update %date% %time:~0,5%"
)

:: ============================================================
:: 4. Git Add
:: ============================================================
echo.
echo [1/4] Staging thay doi...
git add .
if %errorlevel% neq 0 (
    echo [ERROR] git add that bai.
    pause
    exit /b 1
)

:: Kiểm tra có gì để commit không
git diff --cached --quiet >nul 2>&1
if %errorlevel% equ 0 (
    echo [WARN] Khong co thay doi nao de commit.
    echo    ^> Bo qua buoc commit va push.
    pause
    exit /b 0
)

:: ============================================================
:: 5. Git Commit
:: ============================================================
echo.
echo [2/4] Committing...
git commit -m "%COMMIT_MSG%"
if %errorlevel% neq 0 (
    echo [ERROR] git commit that bai.
    pause
    exit /b 1
)

:: ============================================================
:: 6. Git Pull (rebase)
:: ============================================================
echo.
echo [3/4] Pulling tu remote (rebase)...
git pull --rebase origin "%CURRENT_BRANCH%" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] git pull --rebase gap loi ^(co the nhanh chua ton tai tren remote^). Tiep tuc push...
)

:: ============================================================
:: 7. Git Push
:: ============================================================
echo.
echo [4/4] Pushing len GitHub...
git push -u origin "%CURRENT_BRANCH%"
if %errorlevel% neq 0 (
    echo [ERROR] git push that bai!
    echo    ^> Kiem tra ket noi mang, quyen truy cap, hoac conflict.
    pause
    exit /b 1
)

echo.
echo [OK] SYNC HOAN THANH! Nhanh '%CURRENT_BRANCH%' da duoc day len remote.

:: ============================================================
:: 8. Tạo Tag (tùy chọn)
:: ============================================================
echo.
set /p "CREATE_TAG=Tao Tag cho ban nay? (y/N): "
if /i "%CREATE_TAG%"=="y" (
    for /f "tokens=*" %%t in ('git describe --tags --abbrev=0 2^>nul') do (
        echo [INFO] Tag moi nhat hien tai: %%t
    )

    set /p "TAG_NAME=Ten Tag (VD: v1.0.0): "
    if "!TAG_NAME!"=="" (
        echo [WARN] Khong nhap ten Tag. Bo qua.
    ) else (
        set /p "TAG_MSG=Mo ta Tag (Enter de dung commit message): "
        if "!TAG_MSG!"=="" set "TAG_MSG=%COMMIT_MSG%"

        git tag -a "!TAG_NAME!" -m "!TAG_MSG!"
        git push origin "!TAG_NAME!"
        if !errorlevel! equ 0 (
            echo [OK] Da tao va push Tag: !TAG_NAME!
        ) else (
            echo [ERROR] Push Tag that bai.
        )
    )
)

echo.
echo [OK] TAT CA DA HOAN THANH!
pause
