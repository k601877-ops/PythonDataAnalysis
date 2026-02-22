@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 雙北購屋決策分析系統

echo.
echo ================================================
echo     雙北購屋決策分析系統
echo ================================================
echo.
echo 正在啟動視覺化介面，請稍候...
echo.

:: 選擇可用 Python（優先 py -3，其次 python，且排除 WindowsApps 佔位程式）
set "PY_CMD="

py -3 --version >nul 2>&1
if not errorlevel 1 set "PY_CMD=py -3"

if not defined PY_CMD (
    for /f "delims=" %%I in ('where python 2^>nul') do (
        echo %%I | find /I "WindowsApps\python.exe" >nul
        if errorlevel 1 (
            set "PY_CMD=python"
            goto :python_found
        )
    )
)

:python_found
if not defined PY_CMD (
    echo [錯誤] 未檢測到可用 Python 環境
    echo 請先安裝 Python 3.9 或更高版本（安裝時勾選 Add Python to PATH）
    pause
    exit /b 1
)

:: 檢查 Python 版本是否 >= 3.9
%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [錯誤] Python 版本過低，請安裝 Python 3.9 或更高版本
    pause
    exit /b 1
)

for /f "delims=" %%V in ('%PY_CMD% --version 2^>^&1') do set "PY_VER=%%V"
echo [資訊] 使用直譯器：%PY_VER%

:: 檢查 streamlit
%PY_CMD% -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [提示] 首次執行需要安裝依賴套件...
    %PY_CMD% -m pip install --disable-pip-version-check streamlit plotly pandas numpy -q
)

:: 啟動介面
echo [啟動] 視覺化介面啟動中...
echo [提示] 瀏覽器將自動開啟 http://localhost:8501
echo [提示] 關閉此視窗將停止系統
echo.
echo ================================================
echo.

%PY_CMD% -m streamlit run app.py

pause
