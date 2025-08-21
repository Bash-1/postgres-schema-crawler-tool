@echo off
echo ========================================
echo PostgreSQL Schema Crawler - Windows Scheduler Setup
echo ========================================

REM Get the current directory
set "SCRIPT_DIR=%~dp0"
set "PYTHON_PATH=python"

echo Creating scheduled task for daily schema crawling...

REM Create a daily task that runs at 2:00 AM
schtasks /create /tn "PostgreSQL Schema Crawler Daily" /tr "%PYTHON_PATH% %SCRIPT_DIR%run_tool.py" /sc daily /st 02:00 /f

echo.
echo Creating scheduled task for weekly schema comparison...

REM Create a weekly task that runs on Sundays at 3:00 AM
schtasks /create /tn "PostgreSQL Schema Crawler Weekly Report" /tr "%PYTHON_PATH% %SCRIPT_DIR%src\schema_crawler.py diff-latest --output weekly_changes.md" /sc weekly /d SUN /st 03:00 /f

echo.
echo ========================================
echo Scheduled tasks created successfully!
echo ========================================
echo.
echo Tasks created:
echo 1. "PostgreSQL Schema Crawler Daily" - Runs daily at 2:00 AM
echo 2. "PostgreSQL Schema Crawler Weekly Report" - Runs weekly on Sundays at 3:00 AM
echo.
echo To view tasks: schtasks /query /tn "PostgreSQL Schema Crawler*"
echo To delete tasks: schtasks /delete /tn "PostgreSQL Schema Crawler Daily" /f
echo.
pause 