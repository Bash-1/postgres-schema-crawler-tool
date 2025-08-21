#!/bin/bash

echo "========================================"
echo "PostgreSQL Schema Crawler - Linux/Mac Scheduler Setup"
echo "========================================"

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="python3"

echo "Setting up cron jobs for schema crawling..."

# Create a temporary file with the cron jobs
TEMP_CRON=$(mktemp)

# Add daily schema crawling at 2:00 AM
echo "0 2 * * * cd $SCRIPT_DIR && $PYTHON_PATH run_tool.py >> $SCRIPT_DIR/logs/daily_crawl.log 2>&1" >> $TEMP_CRON

# Add weekly schema comparison on Sundays at 3:00 AM
echo "0 3 * * 0 cd $SCRIPT_DIR && $PYTHON_PATH src/schema_crawler.py diff-latest --output weekly_changes.md >> $SCRIPT_DIR/logs/weekly_report.log 2>&1" >> $TEMP_CRON

# Add monthly cleanup of old snapshots (keep last 30 days)
echo "0 4 1 * * cd $SCRIPT_DIR && $PYTHON_PATH src/schema_crawler.py cleanup-old-snapshots --days 30 >> $SCRIPT_DIR/logs/cleanup.log 2>&1" >> $TEMP_CRON

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

# Install the cron jobs
crontab $TEMP_CRON

# Clean up temporary file
rm $TEMP_CRON

echo ""
echo "========================================"
echo "Cron jobs created successfully!"
echo "========================================"
echo ""
echo "Jobs created:"
echo "1. Daily schema crawling - Runs daily at 2:00 AM"
echo "2. Weekly schema comparison - Runs weekly on Sundays at 3:00 AM"
echo "3. Monthly cleanup - Runs monthly on 1st at 4:00 AM"
echo ""
echo "Logs will be saved to:"
echo "- $SCRIPT_DIR/logs/daily_crawl.log"
echo "- $SCRIPT_DIR/logs/weekly_report.log"
echo "- $SCRIPT_DIR/logs/cleanup.log"
echo ""
echo "To view current cron jobs: crontab -l"
echo "To edit cron jobs: crontab -e"
echo "To remove all cron jobs: crontab -r"
echo "" 