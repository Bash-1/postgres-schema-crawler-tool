@echo off
echo ========================================
echo Fix PostgreSQL Schema Crawler Scheduling
echo ========================================
echo.

echo [1/4] Checking administrator privileges...
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] This script requires administrator privileges!
    echo Please run as administrator:
    echo 1. Right-click on this script
    echo 2. Select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo [SUCCESS] Running as administrator

echo.
echo [2/4] Creating scheduled tasks...

echo Creating daily crawler task...
schtasks /create /tn "PostgreSQL Schema Crawler Daily" /tr "cd /d C:\Users\basha\postgres-schema-crawler && python run_tool.py >> logs\daily_crawl.log 2>&1" /sc daily /st 02:00 /f /ru "SYSTEM"

if %errorlevel% equ 0 (
    echo [SUCCESS] Daily task created
) else (
    echo [ERROR] Failed to create daily task
)

echo Creating weekly report task...
schtasks /create /tn "PostgreSQL Schema Crawler Weekly Report" /tr "cd /d C:\Users\basha\postgres-schema-crawler && python src\schema_crawler.py diff-latest --output reports\weekly_changes.md >> logs\weekly_report.log 2>&1" /sc weekly /d SUN /st 03:00 /f /ru "SYSTEM"

if %errorlevel% equ 0 (
    echo [SUCCESS] Weekly task created
) else (
    echo [ERROR] Failed to create weekly task
)

echo.
echo [3/4] Creating reports directory...
if not exist reports mkdir reports

echo.
echo [4/4] Testing tasks...
echo Listing created tasks:
schtasks /query /tn "PostgreSQL Schema Crawler*" /fo table

echo.
echo Running a test crawl now...
python run_tool.py

echo.
echo ========================================
echo Setup Complete!
echo.
echo Tasks created:
echo - Daily crawl: Every day at 2:00 AM
echo - Weekly report: Every Sunday at 3:00 AM
echo.
echo Monitor with: .\monitor_tasks.bat
echo View logs in: logs\ directory
echo View reports in: reports\ directory
echo ========================================
pause