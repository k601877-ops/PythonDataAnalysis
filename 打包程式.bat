@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo 正在將程式打包為 EXE 檔案...
echo ========================================
echo.

:: 檢查 pyinstaller
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [1/3] 安裝 PyInstaller...
    python -m pip install pyinstaller
) else (
    echo [1/3] PyInstaller 已安裝
)
echo.

:: 打包 batch_clean
echo [2/3] 打包資料清理程式...
python -m PyInstaller --onefile --console --name "数据清理" batch_clean_all_years_v2.py --clean
echo.

:: 打包 fix_december
echo [3/3] 打包 12 月補正程式...
python -m PyInstaller --onefile --console --name "12月补正" fix_december.py --clean
echo.

echo ========================================
echo 打包完成！
echo EXE 檔案位置: dist\数据清理.exe
echo              dist\12月补正.exe
echo ========================================
echo.
pause
