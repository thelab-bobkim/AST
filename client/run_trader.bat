@echo off
chcp 65001 > nul
echo [UTF-8 모드로 실행합니다]
cd /d C:\AST\client
call C:\AST\venv32\Scripts\activate.bat
python trader.py
pause
