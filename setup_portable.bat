@echo off
echo ========================================
echo 360 Video Player - Portable Setup
echo ========================================
echo.

echo This script will help you set up the portable package.
echo.

echo Step 1: Download Python
echo Please download Python from https://www.python.org/downloads/
echo Choose Python 3.9 or later
echo.
echo Step 2: Extract Python
echo After downloading, extract the Python folder to the "python" folder
echo in this directory.
echo.
echo Step 3: Run the launcher
echo Once Python is in place, double-click START_360_VIDEO_PLAYER.bat
echo.

pause

echo.
echo Checking if Python is already set up...
if exist "python\python.exe" (
    echo Python found! Testing installation...
    python\python.exe --version
    echo.
    echo Python is ready! You can now run START_360_VIDEO_PLAYER.bat
) else (
    echo Python not found in the python\ folder.
    echo Please download and extract Python as described above.
)

echo.
pause 