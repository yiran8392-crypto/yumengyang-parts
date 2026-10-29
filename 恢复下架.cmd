@echo off
chcp 936 >nul
setlocal EnableDelayedExpansion
title 型号查询站 · 恢复下架
color 0F

set "SITE=%~dp0"
if exist "%SITE%型号查询站\data\data.js" set "SITE=%SITE%型号查询站"
set "PY=D:\欧鲸鲸\dsh-home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

echo ==================================================
echo   型号查询站 · 恢复下架（撤销「只有我方 SKU」下架）
echo ==================================================
echo.

if not exist "%SITE%data\data.js" goto nodir
if not exist "%PY%" goto nopy
if not exist "%SITE%_backup" goto nobackup

echo 可用的备份：
for /f "delims=" %%d in ('dir /b /ad /o-n "%SITE%_backup\下架前-*" 2^>nul') do echo    - %%d
echo.

set "LAST="
for /f "delims=" %%d in ('dir /b /ad /o-n "%SITE%_backup\下架前-*" 2^>nul') do (
  if not defined LAST set "LAST=%%d"
)
if not defined LAST goto nobackup
set "BKDIR=%SITE%_backup\%LAST%"
if not exist "%BKDIR%\data.js" goto nobackup

echo 将要用这个备份恢复：%LAST%
echo.
set "YN="
set /p "YN=确定恢复吗？(Y/N) "
if /i not "!YN!"=="Y" goto cancel
echo.

echo [1/3] 还原 data.js 和 sitegen.py …
copy /y "%BKDIR%\data.js" "%SITE%data\data.js" >nul
if exist "%BKDIR%\sitegen.py" copy /y "%BKDIR%\sitegen.py" "%SITE%sitegen.py" >nul
echo      好了。

echo [2/3] 重新生成所有页面 …
"%PY%" "%SITE%rerender.py"
if errorlevel 1 goto rendfail
echo      页面重建完成。

echo [3/3] 同步内部版 …
if exist "D:\欧鲸鲸\default-workspace\型号查询站-内部版\build_internal.py" (
  "%PY%" "D:\欧鲸鲸\default-workspace\型号查询站-内部版\build_internal.py" >nul 2>&1
  echo      内部版已重建（带价格，只在本机）。
) else (
  echo      没找到内部版，跳过。
)

echo.
echo ==================================================
echo   恢复完成！型号数已回到下架前。
echo ==================================================
echo.
set "PUB="
set /p "PUB=现在要不要发布到线上？(Y/N) "
if /i "!PUB!"=="Y" (
  call "%SITE%发布上线.cmd"
) else (
  echo 好的，只在本机生效。想发布时双击 发布上线.cmd 即可。
  pause
)
exit /b 0

:cancel
echo 已取消，什么都没改。
pause
exit /b 0

:nodir
echo [错误] 这个文件夹里没找到站点的 data\data.js。
echo        请把 恢复下架.cmd 放到 型号查询站 或它的上一级文件夹里。
pause
exit /b 1

:nopy
echo [错误] 找不到自带的 Python：
echo        %PY%
pause
exit /b 1

:nobackup
echo [错误] 在 _backup 里没找到「下架前-*」备份目录。
echo        备份应该在 %SITE%_backup\ 下面，里面有 data.js。
pause
exit /b 1

:rendfail
echo.
echo [错误] 页面重建失败，data.js 已经还原了，但页面还是旧的。
echo        把上面红字截图给技术看，或者再双击一次本文件。
pause
exit /b 1
