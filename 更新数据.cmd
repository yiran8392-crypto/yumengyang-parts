@echo off
chcp 936 >nul
setlocal
title 型号查询站 - 更新数据
cd /d "%~dp0"
set "PYTHONIOENCODING=gbk"
set "PY=D:\欧鲸鲸\dsh-home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

echo ==================================================
echo   型号查询站 · 更新数据
echo ==================================================
echo.

if not exist "%PY%" goto no_python
if not exist "build.py" goto no_script

echo 正在扫描 Excel、重新生成数据和图片……
echo 第一次可能要几分钟（两千多张图要压缩），之后会快很多。
echo 过程中别关这个窗口。
echo.

"%PY%" "build.py"
if errorlevel 1 goto failed

echo.
echo ==================================================
echo   完成！现在双击 index.html 就能看到新数据。
echo ==================================================
echo.
pause
exit /b 0

:no_python
echo [错误] 找不到 Python 运行环境：
echo        %PY%
echo.
echo 这个环境是电脑里自带的，可能被卸载或者挪走了。
echo 请把它放回原位置，或者找懂电脑的同事帮忙。
echo.
pause
exit /b 1

:no_script
echo [错误] 当前文件夹里没有 build.py。
echo        可能被误删了，请把整个“型号查询站”文件夹重新复制一份。
echo.
pause
exit /b 1

:failed
echo.
echo ==================================================
echo   失败：更新没有完成，具体原因看上面几行。
echo --------------------------------------------------
echo   常见原因：
echo     1. 某个 Excel 被改名、移动或者删掉了
echo     2. Excel 正被 Excel 软件打开占用着
echo     3. 磁盘空间不够（尤其是 D 盘）
echo ==================================================
echo.
pause
exit /b 1