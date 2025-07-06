@echo off
echo DATABASE LOCK FIX UTILITY
echo ========================

echo Killing any Python processes...
taskkill /f /im python.exe 2>nul
taskkill /f /im pythonw.exe 2>nul

echo Waiting 2 seconds...
timeout /t 2 /nobreak >nul

echo Checking database file...
if exist "\\wsl.localhost\Ubuntu\home\gyashu\projects\mini_search_engine\data\processed\documents.db" (
    echo Database file found
) else (
    echo Database file NOT found
    exit /b 1
)

echo Done! Try running the demo now:
echo   python demo_simple.py
echo   python demo.py

pause
