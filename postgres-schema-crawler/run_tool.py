#!/usr/bin/env python3
"""
PostgreSQL Schema Crawler - One Command Launcher

This script runs the complete tool with a single command:
1. Crawls the current schema
2. Launches the Streamlit web application
3. Provides status updates throughout the process

Usage: python run_tool.py
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_status(message, status_type="info"):
    """Print formatted status messages."""
    colors = {
        "info": "\033[94m",    # Blue
        "success": "\033[92m", # Green
        "warning": "\033[93m", # Yellow
        "error": "\033[91m",   # Red
        "bold": "\033[1m",     # Bold
        "reset": "\033[0m"     # Reset
    }
    
    timestamp = time.strftime("%H:%M:%S")
    color = colors.get(status_type, colors["info"])
    print(f"{color}[{timestamp}] {message}{colors['reset']}")

def check_dependencies():
    """Check if all required dependencies are installed."""
    print_status("Checking dependencies...", "info")
    
    required_packages = [
        "psycopg2-binary",
        "sqlalchemy", 
        "pandas",
        "pyyaml",
        "click",
        "rich",
        "streamlit",
        "plotly"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print_status(f"✓ {package}", "success")
        except ImportError:
            missing_packages.append(package)
            print_status(f"✗ {package} - MISSING", "error")
    
    if missing_packages:
        print_status("Installing missing packages...", "warning")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing_packages, 
                         check=True, capture_output=True)
            print_status("All dependencies installed successfully!", "success")
        except subprocess.CalledProcessError as e:
            print_status(f"Failed to install dependencies: {e}", "error")
            return False
    
    return True

def check_database_connection():
    """Test database connection before proceeding."""
    print_status("Testing database connection...", "info")
    
    try:
        # Import and test connection
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        from schema_crawler import DatabaseConnection
        
        db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'temp1',
            'user': 'postgres',
            'password': 'Kingkong@1'
        }
        
        db_conn = DatabaseConnection(**db_config)
        if db_conn.connect():
            print_status("✓ Database connection successful!", "success")
            db_conn.disconnect()
            return True
        else:
            print_status("✗ Database connection failed!", "error")
            return False
            
    except Exception as e:
        print_status(f"✗ Database connection error: {e}", "error")
        return False

def crawl_schema(table_filter=None):
    """Crawl the current schema and save snapshot."""
    print_status("Crawling current schema...", "info")
    
    # Build command with optional table filtering
    command = [sys.executable, "src/schema_crawler.py", "crawl"]
    
    if table_filter:
        print_status("Applying table filters...", "info")
        
        # Add include tables
        if table_filter.get('include_tables'):
            for table in table_filter['include_tables']:
                command.extend(['--include-tables', table])
        
        # Add exclude tables
        if table_filter.get('exclude_tables'):
            for table in table_filter['exclude_tables']:
                command.extend(['--exclude-tables', table])
        
        # Add include patterns
        if table_filter.get('include_patterns'):
            for pattern in table_filter['include_patterns']:
                command.extend(['--include-patterns', pattern])
        
        # Add exclude patterns
        if table_filter.get('exclude_patterns'):
            for pattern in table_filter['exclude_patterns']:
                command.extend(['--exclude-patterns', pattern])
        
        # Add case sensitive flag
        if table_filter.get('case_sensitive'):
            command.append('--case-sensitive')
    
    try:
        # Run schema crawler
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        print_status("✓ Schema crawl completed successfully!", "success")
        return True
        
    except subprocess.CalledProcessError as e:
        print_status(f"✗ Schema crawl failed: {e.stderr}", "error")
        return False

def launch_streamlit():
    """Launch the Streamlit web application."""
    print_status("Launching Streamlit web application...", "info")
    
    # Choose which web UI to launch (enhanced version with user attribution)
    web_ui_file = "enhanced_web_ui.py"
    
    if not os.path.exists(web_ui_file):
        web_ui_file = "src/web_ui.py"
    
    print_status(f"Using web UI: {web_ui_file}", "info")
    
    try:
        # Launch Streamlit in the background
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", web_ui_file,
            "--server.port", "8501",
            "--server.headless", "true"
        ])
        
        # Wait a moment for Streamlit to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print_status("✓ Streamlit application launched successfully!", "success")
            print_status("Web application is running at: http://localhost:8501", "success")
            print_status("Press Ctrl+C to stop the application", "warning")
            
            # Keep the process running
            try:
                process.wait()
            except KeyboardInterrupt:
                print_status("Stopping Streamlit application...", "warning")
                process.terminate()
                process.wait()
                print_status("Application stopped.", "info")
            
            return True
        else:
            print_status("✗ Failed to launch Streamlit application", "error")
            return False
            
    except Exception as e:
        print_status(f"✗ Error launching Streamlit: {e}", "error")
        return False

def show_summary():
    """Show a summary of what was accomplished."""
    print_status("=" * 60, "bold")
    print_status("PostgreSQL Schema Crawler - Summary", "bold")
    print_status("=" * 60, "bold")
    
    # Check if we have snapshots
    db_path = "data/schema_metadata.db"
    if os.path.exists(db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM schema_snapshots")
        snapshot_count = cursor.fetchone()[0]
        conn.close()
        
        print_status(f"✓ {snapshot_count} schema snapshots available", "success")
    else:
        print_status("✗ No schema snapshots found", "error")
    
    print_status("✓ Web application ready at: http://localhost:8501", "success")
    print_status("✓ CLI commands available:", "success")
    print_status("  - python src/schema_crawler.py crawl", "info")
    print_status("  - python src/schema_crawler.py list-snapshots", "info")
    print_status("  - python src/schema_crawler.py diff-latest", "info")
    print_status("=" * 60, "bold")

def main():
    """Main function to run the complete tool."""
    print_status("PostgreSQL Schema Crawler - One Command Launcher", "bold")
    print_status("=" * 60, "bold")
    
    # Step 1: Check dependencies
    if not check_dependencies():
        print_status("Failed to resolve dependencies. Please install required packages.", "error")
        return False
    
    print_status("✓ All dependencies are available", "success")
    
    # Step 2: Check database connection
    if not check_database_connection():
        print_status("Database connection failed. Please check your configuration.", "error")
        print_status("Edit config.yaml or update the database settings in this script.", "warning")
        return False
    
    print_status("✓ Database connection verified", "success")
    
    # Step 3: Check for table filter configuration
    table_filter = None
    try:
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            table_filter = config.get('crawler', {}).get('table_filter', {})
            
            # Check if any filter is configured
            if (table_filter.get('include_tables') or 
                table_filter.get('exclude_tables') or 
                table_filter.get('include_patterns') or 
                table_filter.get('exclude_patterns')):
                print_status("Table filtering configuration found in config.yaml", "info")
                for key, value in table_filter.items():
                    if value:  # Only show non-empty filters
                        print_status(f"  {key}: {value}", "info")
    except Exception as e:
        print_status(f"Could not load config.yaml: {e}", "warning")
    
    # Step 4: Crawl current schema
    if not crawl_schema(table_filter):
        print_status("Schema crawling failed. Please check the error messages above.", "error")
        return False
    
    print_status("✓ Schema crawling completed", "success")
    
    # Step 5: Show summary
    show_summary()
    
    # Step 6: Launch Streamlit
    print_status("Launching web interface...", "info")
    return launch_streamlit()

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print_status("\nApplication interrupted by user.", "warning")
        sys.exit(0)
    except Exception as e:
        print_status(f"Unexpected error: {e}", "error")
        sys.exit(1) 