@echo off
chcp 65001 >nul
cd /d "%~dp0"
python lava_craft_3d.py
pause
