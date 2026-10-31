@echo off
chcp 65001 >nul
cd /d "%~dp0"
python heif2dng.py --input "W:\Travel\2022\iPhone\DJY\HEIF" --output "W:\Travel\2022\iPhone\DJY\DNG" --force --compression uncompressed
echo.
pause
