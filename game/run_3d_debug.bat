@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Debug mode: F1-F8 test keys
python lava_craft_3d.py --debug
pause
