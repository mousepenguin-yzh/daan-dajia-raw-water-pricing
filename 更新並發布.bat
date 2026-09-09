@echo off
chcp 65001 >nul
title 大安大甲聯合運用 - 更新並發布
cd /d "%~dp0"

echo.
echo === 大安大甲聯合運用 - 原水費計價情境網頁 ===
echo.
py -3 update_and_publish.py
if errorlevel 1 (
  echo.
  echo 更新未完成，上一版網頁不受影響。
  echo.
  pause
  exit /b 1
)

echo.
echo 更新流程完成。
echo.
pause
