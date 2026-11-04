@echo off
chcp 936 >nul
setlocal
title 型号查询站 - 更新数据
cd /d "%~dp0"
set "PYTHONIOENCODING=gbk"
set "PY=D:\欧鲸鲸\dsh-home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

echo ==================================================
echo   型号查询站 . 更新数据
echo ==================================================
echo.

if not exist "%PY%" goto no_python
if not exist "update_all.py" goto no_script

echo 正在读目录表补型号、重新生成页面……
echo 先自动备份 data\data.js，出问题能还原。
echo 过程中别关这个窗口。
echo.

"%PY%" "update_all.py"
if errorlevel 1 goto failed

echo.
echo ==================================================
echo   完成！现在双击 index.html 就能看到新数据。
echo ==================================================
echo.
pause
exit /b 0

:no_python
echo 找不到 Python：%PY%
echo 把 D:\欧鲸鲸\dsh-home\dsh-runtimes 这个运行时目录放回原位，或改本文件里的 PY 路径。
pause
exit /b 1

:no_script
echo 找不到 update_all.py，请确认解压完整。
pause
exit /b 1

:failed
echo.
echo !! 更新失败。data\data.js.bak-* 是更新前的备份，可以拿回来还原。
pause
exit /b 1
