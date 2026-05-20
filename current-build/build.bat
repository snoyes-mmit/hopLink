@echo off
REM build.bat — Windows wrapper for build_tools/build.py
REM Usage: build.bat [--mode onedir|onefile] [--debug] [--clean]

setlocal

REM Locate Python. Prefer `py` launcher (standard on Windows) over `python`,
REM since `python` on Windows often points to the Microsoft Store stub.
where py >nul 2>nul
if %ERRORLEVEL% == 0 (
    set "PYTHON=py -3"
) else (
    set "PYTHON=python"
)

%PYTHON% "%~dp0build_tools\build.py" %*
exit /b %ERRORLEVEL%
