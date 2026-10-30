@echo off
chcp 936 >nul
setlocal
title 型号查询站 - 提交收录 IndexNow
cd /d "%~dp0"
set "PYTHONIOENCODING=gbk:replace"
set "PY=D:\欧鲸鲸\dsh-home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

echo ==================================================
echo   型号查询站 · 提交收录（IndexNow）
echo --------------------------------------------------
echo   Bing / Yandex / Seznam 都吃这个，不用注册账号。
echo   Google 不吃，它自己看 sitemap。
echo ==================================================
echo.

if not exist "indexnow_submit.py" goto no_script
if not exist "sitemap.xml" goto no_sitemap
if exist "%PY%" goto run
where python >nul 2>&1
if errorlevel 1 goto no_python
set "PY=python"

:run
echo 正在提交 sitemap.xml 里的全部 URL……
echo 想先试水：把下一行照抄到命令提示符里跑  %~nx0 --limit 20
echo.
"%PY%" "indexnow_submit.py" %*
if errorlevel 1 goto failed

echo.
echo ==================================================
echo   完成：接口已接收（200 / 202）。
echo   接收不等于马上有收录，一般几天到两周在 Bing 里能看到。
echo ==================================================
echo.
pause
exit /b 0

:no_script
echo [错误] 当前文件夹里没有 indexnow_submit.py。
echo        可能被误删了，把整个“型号查询站”文件夹重新复制一份。
echo.
pause
exit /b 1

:no_sitemap
echo [错误] 当前文件夹里没有 sitemap.xml。
echo        先双击“重新生成页面.cmd”（或跑 rerender.py）再提交。
echo.
pause
exit /b 1

:no_python
echo [错误] 找不到 Python 运行环境：
echo        %PY%
echo        这个环境是电脑里自带的，可能被卸载或挪走了。
echo.
pause
exit /b 1

:failed
echo.
echo ==================================================
echo   失败：URL 没提交成功，具体原因看上面几行。
echo --------------------------------------------------
echo   常见原因：
echo     1. 返回 403：key 文件没对上
echo        （https://你的域名/xxx.txt 打不开，或文件内容不是那串 key）
echo     2. 返回 400：URL 和 host 不一致（“域名=”填错了）
echo     3. 返回 429：提交太频繁，隔几小时再试
echo     4. 上面一行是空的：电脑里的 python 是个占位程序，
echo        请改用 %PY%
echo ==================================================
echo.
pause
exit /b 1
