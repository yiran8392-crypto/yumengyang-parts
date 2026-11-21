@echo off
chcp 936 >nul
setlocal
set "HERE=%~dp0"
set "PY="

if exist "D:\欧鲸鲸\dsh-home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" (
  "D:\欧鲸鲸\dsh-home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PY=D:\欧鲸鲸\dsh-home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
)
if not defined PY (
  python -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo [!] 找不到能用的 Python 3。
  pause
  exit /b 1
)

echo ============================================================
echo  生成多语种静态页（ar / ru / es / pt）
echo ============================================================
echo.
echo  什么时候跑：
echo    · 每次双击完 更新数据.cmd 之后，必须再跑一次这个 ——
echo      因为重建站点会把英文页的 hreflang 冲掉。
echo    · 改了译名（i18n.js 的 T / C，或 pdata_i18n.py）之后也要跑。
echo.
pause

echo.
echo [1/4] 从 i18n.js 提取翻译表…
"%PY%" "%HERE%i18n_extract.py"
if errorlevel 1 goto fail

echo.
echo [2/4] 生成 4 个语种的静态页…
"%PY%" "%HERE%mk_lang_sites.py"
if errorlevel 1 goto fail

echo.
echo [3/4] 给英文原页补 hreflang 互指…
"%PY%" "%HERE%mk_lang_sites.py" --en
if errorlevel 1 goto fail

echo.
echo [4/4] 把多语页面收进 sitemap…
"%PY%" "%HERE%mk_lang_sites.py" --sitemap
if errorlevel 1 goto fail

echo.
echo ============================================================
echo  完成。检查一下再发布：
echo    "%%PY%%" "%%HERE%%validate.py"
echo    "%%PY%%" "%%HERE%%_selftest\verify_geo.py"
echo  都没问题再双击 发布上线.cmd
echo ============================================================
pause
exit /b 0

:fail
echo.
echo [!] 出错了，看上面的报错。没有生成的部分不会覆盖旧文件。
pause
exit /b 1