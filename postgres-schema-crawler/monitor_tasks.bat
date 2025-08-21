@echo off
echo ========================================
echo PostgreSQL Schema Crawler - Task Monitor
echo ========================================
echo.

echo [1/4] Checking scheduled tasks...
schtasks /query /tn "PostgreSQL Schema Crawler*" /fo table 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] No PostgreSQL Schema Crawler tasks found!
    echo Run the setup script as Administrator: .\schedule_windows.bat
) else (
    echo [SUCCESS] Tasks found and configured
)

echo.
echo [2/4] Checking recent logs...
if exist logs\daily_crawl.log (
    echo Last 5 lines of daily crawl log:
    powershell "Get-Content logs\daily_crawl.log | Select-Object -Last 5"
) else (
    echo [INFO] No daily crawl log found yet
)

if exist logs\scheduled_crawler.log (
    echo Last 5 lines of scheduler log:
    powershell "Get-Content logs\scheduled_crawler.log | Select-Object -Last 5"
) else (
    echo [INFO] No scheduler log found yet
)

echo.
echo [3/4] Checking database snapshots...
if exist data\schema_metadata.db (
    echo [SUCCESS] Database file exists
    for %%F in (data\schema_metadata.db) do echo Size: %%~zF bytes, Modified: %%~tF
) else (
    echo [INFO] No database file found yet
)

echo.
echo [4/4] Checking configuration...
if exist config.yaml (
    echo [SUCCESS] Configuration file found
    echo Table filter: employees (from config.yaml)
) else (
    echo [WARNING] Configuration file not found
)

echo.
echo ========================================
echo Quick Commands:
echo - View all tasks: schtasks /query /fo table ^| findstr "PostgreSQL"
echo - Run task now: schtasks /run /tn "PostgreSQL Schema Crawler Daily"
echo - Test manually: python run_tool.py
echo - Open Task Scheduler: taskschd.msc
echo ========================================
pause 