#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "启动服务，请用浏览器打开：http://127.0.0.1:8010"
echo "（Ctrl+C 停止）"
exec python3 -m backend.main
