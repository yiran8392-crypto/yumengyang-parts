@echo off
chcp 936 >nul
setlocal
title 型号查询站 - 收录检查
cd /d "%~dp0"
set "PYTHONIOENCODING=gbk:replace"
set "PY=D:\欧鲸鲸\dsh-home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
set "PY_BUNDLED=%PY%"

echo ==================================================
echo   型号查询站 · 收录检查
echo --------------------------------------------------
echo   跑一次，出一份中文报告（同文件夹里的 md 文件）。
echo   检查：sitemap 条数 / 线上能否打开 /
echo         Bing、Yandex 收录 / IndexNow 的 key。
echo   大约 30 秒，别关窗口。
echo ==================================================
echo.

if not exist "收录检查.py" goto no_script
if not exist "sitemap.xml" goto no_sitemap

if exist "%PY%" goto have_python
rem 电脑自带的那个 python 先试试（有的电脑装的是微软商店的占位程序，会失败）
where python >nul 2>&1
if errorlevel 1 goto no_python
set "PY=python"

:have_python
"%PY%" -c "import sys" >nul 2>&1
if errorlevel 1 goto no_python

echo 正在检查……
echo.
"%PY%" "收录检查.py" %*
if errorlevel 1 goto failed

echo.
echo ==================================================
echo   完成。报告在这个文件夹里：
echo   收录检查报告-日期-时间.md
echo   双击就能用记事本打开看。
echo ==================================================
echo.
pause
exit /b 0

:no_script
echo [错误] 找不到 收录检查.py。
echo        它应该和这个 cmd 文件在同一个文件夹里。
echo        把整个“型号查询站”文件夹重新复制一份就好。
echo.
pause
exit /b 1

:no_sitemap
echo [错误] 找不到 sitemap.xml。
echo        先双击“重新生成页面.cmd”把站点生成出来，再来检查。
echo.
pause
exit /b 1

:no_python
echo [错误] 找不到能用的 Python，两个地方都没找到：
echo          1) %PY_BUNDLED%
echo             （随工作台一起装的，可能被卸载或挪走了）
echo          2) 系统 PATH 里的 python
echo             （有的话可能是个占位程序，跑起来是空的）
echo.
echo        换台电脑的话：装 Python 3，安装时勾选 Add Python to PATH；
echo        或者把工作台目录恢复回来，再双击本文件。
echo.
pause
exit /b 1

:failed
echo.
echo ==================================================
echo   检查中断了，具体原因看上面几行。
echo --------------------------------------------------
echo   常见情况：
echo     1. 网络断了 / 公司网络拦了：连不上网站，
echo        报告里会写“连不上”，换个网络再跑。
echo     2. 卡在“正在检查……”后就没反应：杀毒软件拦了 python，
echo        把它加进白名单再来。
echo     3. 中文变成乱码：窗口字体不支持，报告文件本身是好的。
echo ==================================================
echo.
pause
exit /b 1
