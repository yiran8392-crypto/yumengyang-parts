@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion
title 型号查询站 · 一键发布
color 0F

set "HERE=%~dp0"
set "SITE=%HERE%"
if exist "%HERE%型号查询站\data\data.js" set "SITE=%HERE%型号查询站"
set "TOKFILE=D:\欧鲸鲸\tools\gh_token.txt"
set "LIVE=https://yiran8392-crypto.github.io/yumengyang-parts/"

echo ==================================================
echo   型号查询站 · 一键发布到线上
echo ==================================================
echo.

where git >nul 2>&1
if errorlevel 1 goto nogit

cd /d "%SITE%"
if not exist "data\data.js" goto wrongdir
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 goto norepo

echo [1/4] 正在检查改动……
git add -A >nul 2>&1
git diff --cached --quiet
if errorlevel 1 goto do_commit

rem 没有新改动：看看是不是上次推送失败了，还有提交压在本地
set "AHEAD=0"
for /f %%n in ('git rev-list --count origin/main..HEAD 2^>nul') do set "AHEAD=%%n"
if "%AHEAD%"=="0" goto nochanges
echo     没有新改动，但本地有 %AHEAD% 个提交还没推上去，继续发布……
goto do_push

:do_commit
echo [2/4] 有改动，准备提交……
set "STAMP="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"`) do set "STAMP=%%i"
if "%STAMP%"=="" set "STAMP=update"
git -c user.name="yiran8392-crypto" -c user.email="yiran8392@users.noreply.github.com" commit -q -m "Update %STAMP%"
if errorlevel 1 goto commitfail
echo     已提交：Update %STAMP%

:do_push
echo [3/4] 正在推送……
if not exist "%TOKFILE%" goto notoken
set "TOKEN="
set /p TOKEN=<"%TOKFILE%"
if "%TOKEN%"=="" goto notoken

for /f "delims=" %%r in ('git config --get remote.origin.url') do set "ORIG=%%r"
if "%ORIG%"=="" goto noremote
set "CLEAN=%ORIG%"
if not "%ORIG%"=="%ORIG:@=%" for /f "tokens=1,* delims=@" %%a in ("%ORIG%") do set "CLEAN=https://%%b"
set "PUSHURL=https://x-access-token:%TOKEN%@%CLEAN:https://=%"

set "LOG=%TEMP%\ymy_push.log"
git remote set-url origin "%PUSHURL%"
git push origin HEAD >"%LOG%" 2>&1
set "RC=!errorlevel!"
if not "!RC!"=="0" (
  findstr /C:"SEC_E_NO_CREDENTIALS" "%LOG%" >nul
  if !errorlevel!==0 (
    echo     系统 TLS 有点小脾气，自动换个方式重试……
    git -c http.sslBackend=openssl push origin HEAD >"%LOG%" 2>&1
    set "RC=!errorlevel!"
  )
)
if not "!RC!"=="0" (
  echo     连接不太稳，再试 2 次……
  for /l %%k in (1,1,2) do (
    if not "!RC!"=="0" (
      timeout /t 5 /nobreak >nul
      git -c http.sslBackend=openssl push origin HEAD >"%LOG%" 2>&1
      set "RC=!errorlevel!"
    )
  )
)
git remote set-url origin "%CLEAN%"
if not "!RC!"=="0" goto pushfail

echo [4/4] 发布完成！
echo.
echo   线上地址（GitHub Pages 一般 1 分钟内置新）：
echo     %LIVE%
echo   打开后没变化就按 Ctrl+F5 强制刷新一下。
echo.
start "" "%LIVE%"
goto ok

:nochanges
echo     没有改动，无需发布。
echo.
echo   线上地址：%LIVE%
goto ok

:nogit
echo.
echo [错误] 这台电脑上没找到 git 命令。
echo        发布需要先安装 Git for Windows（装完重开本窗口再双击一次）。
goto fail

:wrongdir
echo.
echo [错误] 这个文件夹里没找到站点的 data\data.js。
echo        请把 发布上线.cmd 放在 型号查询站 文件夹里，或者放在它的上一级文件夹。
goto fail

:norepo
echo.
echo [错误] 这个文件夹不是 git 仓库（找不到 .git）。
echo        站点文件夹可能被拷来拷去，请在原来是仓库的那份上发布。
goto fail

:notoken
echo.
echo [错误] 找不到 token 文件，或者文件是空的：
echo        %TOKFILE%
echo        没有它推不上去。请把 GitHub 的 personal access token 存进这个文件（一行，别加空格）。
goto fail

:noremote
echo.
echo [错误] 这个仓库没配置 origin（远程地址）。
echo        请先运行一次：git remote add origin https://github.com/yiran8392-crypto/yumengyang-parts.git
goto fail

:commitfail
echo.
echo [错误] 提交失败，没往下走。
echo        常见原因：别的程序正占着 .git 里的文件，或者磁盘满了。
goto fail

:pushfail
echo.
echo [错误] 推送失败，线上没有更新。
echo        原因多半是下面这几种：
echo          1. token 过期或没权限（重新生成一个放到 %TOKFILE%）
echo          2. 电脑连不上 GitHub（看看网络）
echo        详细日志：
echo          %LOG%
echo.
type "%LOG%"
goto fail

:ok
echo ==================================================
echo   完成。可以直接关窗口。
echo ==================================================
echo.
pause
exit /b 0

:fail
echo.
echo 上面那条错误解决以后，重新双击 发布上线.cmd 就行。
pause
exit /b 1
