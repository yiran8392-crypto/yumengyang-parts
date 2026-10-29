@echo off
chcp 936 >nul
setlocal
title 型号查询站 · 本地预览
color 0F

set "HERE=%~dp0"
set "SITE=%HERE%"
if exist "%HERE%型号查询站\data\data.js" set "SITE=%HERE%型号查询站"
set "PY=D:\欧鲸鲸\dsh-home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
set "PORT=8000"

echo ==================================================
echo   型号查询站 · 本地预览
echo ==================================================
echo.

if not exist "%PY%" goto nopy
if not exist "%SITE%data\data.js" goto nodir

echo 正在启动本地服务（端口 %PORT%）……
start "型号查询站 · 本地预览服务（关掉这个窗口就停止）" /D "%SITE%" "%PY%" -m http.server %PORT% --bind 127.0.0.1
ping -n 3 127.0.0.1 >nul
start "" "http://127.0.0.1:%PORT%/index.html"

echo.
echo   预览地址： http://127.0.0.1:%PORT%/
echo   首页：     http://127.0.0.1:%PORT%/index.html
echo.
echo   改完文件按 F5 刷新就能看到（CSS/HTML 立刻生效，data.js 也从新读）。
echo   想改端口：用记事本打开本文件，把 set "PORT=%PORT%" 那行的数字改掉。
echo   停服务：   关掉“型号查询站 · 本地预览服务”那个黑窗口。
echo.
pause
exit /b 0

:nopy
echo [错误] 找不到自带的 Python：
echo        %PY%
echo        这个运行环境可能被挪走了，请把它放回原位置。
pause
exit /b 1

:nodir
echo [错误] 这个文件夹里没找到站点的 data\data.js。
echo        请把 本地预览.cmd 放在 型号查询站 文件夹里，或者放在它的上一级文件夹。
pause
exit /b 1
