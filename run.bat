@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 启动服务，请用浏览器打开：http://127.0.0.1:8010
echo （Ctrl+C 停止）
python -m backend.main
pause
