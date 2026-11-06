@echo off
chcp 936 >nul
setlocal
title 型号查询站 - 切换正式域名
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "PY=D:\欧鲸鲸\dsh-home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

echo ==================================================
echo   型号查询站 . 切换到 parts.yumengyang.com
echo ==================================================
echo.

if not exist "%PY%" goto no_python
if not exist "切换域名.py" goto no_script

"%PY%" "切换域名.py" %*
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%

:no_python
echo 找不到 Python：%PY%
echo 把 D:\欧鲸鲸\dsh-home\dsh-runtimes 这个运行时目录放回原位。
pause
exit /b 1

:no_script
echo 找不到 切换域名.py，请确认它跟本文件在同一个文件夹。
pause
exit /b 1
