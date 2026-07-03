@echo off
cd /d c:\Vidushi\Indian_Add_Geo
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe _run_tests.py
) else (
    python _run_tests.py
)
exit /b %ERRORLEVEL%
