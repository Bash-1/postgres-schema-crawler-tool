#!/usr/bin/env python3
"""
Scheduled PostgreSQL Schema Crawler

This script runs the schema crawler on a schedule and handles logging,
error reporting, and notifications.
"""

import schedule
import time
import logging
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

# Configure logging
def setup_logging():
    """Setup logging configuration."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "scheduled_crawler.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def run_schema_crawl():
    """Run the schema crawler and log results."""
    logger = logging.getLogger(__name__)
    logger.info("Starting scheduled schema crawl...")
    
    try:
        # Run the schema crawler
        result = subprocess.run([
            sys.executable, "run_tool.py"
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            logger.info("Schema crawl completed successfully")
            logger.info(f"Output: {result.stdout}")
        else:
            logger.error(f"Schema crawl failed with return code {result.returncode}")
            logger.error(f"Error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logger.error("Schema crawl timed out after 5 minutes")
    except Exception as e:
        logger.error(f"Unexpected error during schema crawl: {e}")

def run_schema_comparison():
    """Run schema comparison and generate report."""
    logger = logging.getLogger(__name__)
    logger.info("Starting scheduled schema comparison...")
    
    try:
        # Generate weekly comparison report
        report_file = f"reports/weekly_changes_{datetime.now().strftime('%Y%m%d')}.md"
        os.makedirs("reports", exist_ok=True)
        
        result = subprocess.run([
            sys.executable, "src/schema_crawler.py", "diff-latest", 
            "--output", report_file
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logger.info(f"Schema comparison completed successfully. Report: {report_file}")
        else:
            logger.error(f"Schema comparison failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Error during schema comparison: {e}")

def cleanup_old_snapshots():
    """Clean up old snapshots to save space."""
    logger = logging.getLogger(__name__)
    logger.info("Starting cleanup of old snapshots...")
    
    try:
        # Keep only last 30 days of snapshots
        result = subprocess.run([
            sys.executable, "src/schema_crawler.py", "cleanup-old-snapshots", 
            "--days", "30"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            logger.info("Cleanup completed successfully")
        else:
            logger.error(f"Cleanup failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def send_notification(message, level="INFO"):
    """Send notification about crawl results."""
    logger = logging.getLogger(__name__)
    
    # You can integrate with email, Slack, Teams, etc.
    # For now, just log the notification
    logger.info(f"NOTIFICATION [{level}]: {message}")
    
    # Example: Send email notification
    # import smtplib
    # from email.mime.text import MIMEText
    # # ... email sending code here

def main():
    """Main function to run the scheduled crawler."""
    logger = setup_logging()
    logger.info("Starting PostgreSQL Schema Crawler Scheduler")
    
    # Schedule jobs
    schedule.every().day.at("02:00").do(run_schema_crawl)
    schedule.every().sunday.at("03:00").do(run_schema_comparison)
    schedule.every().month.at("04:00").do(cleanup_old_snapshots)
    
    # Optional: Run immediately on startup
    if len(sys.argv) > 1 and sys.argv[1] == "--run-now":
        logger.info("Running initial crawl...")
        run_schema_crawl()
    
    logger.info("Scheduler started. Jobs scheduled:")
    logger.info("- Daily schema crawl: 02:00 AM")
    logger.info("- Weekly comparison: Sunday 03:00 AM")
    logger.info("- Monthly cleanup: 1st of month 04:00 AM")
    
    # Keep the script running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")

if __name__ == "__main__":
    main() 