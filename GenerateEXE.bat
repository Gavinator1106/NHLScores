@echo off
echo ========================================
echo Building NHL Scores EXE
echo ========================================
echo.

echo Installing PyInstaller (if needed)...
pip install pyinstaller

echo.
echo Building EXE file...
python -m PyInstaller --onefile --windowed --name "NHLScores" --add-data "logos;logos" NHLscores.py

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Your EXE file is located at:
echo %CD%\dist\NHLScores.exe
echo.
echo To use it:
echo 1. Copy NHLScores.exe from the 'dist' folder
echo 2. Copy the 'logos' folder to the same location
echo 3. Double-click NHLScores.exe to run!
echo.
pause