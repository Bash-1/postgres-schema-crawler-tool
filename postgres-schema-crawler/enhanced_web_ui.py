#!/usr/bin/env python3
"""
Enhanced Web UI with User Tracking
Shows who made schema changes in the Streamlit dashboard.
"""

import streamlit as st
import sqlite3
import json
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

def get_ddl_changes_for_snapshots(snapshot1_id, snapshot2_id):
    """Get DDL changes between two snapshots."""
    try:
        # Get snapshot timestamps
        conn = sqlite3.connect('data/schema_metadata.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT timestamp FROM schema_snapshots WHERE id = ?", (snapshot1_id,))
        result = cursor.fetchone()
        if not result:
            return []
        snapshot1_time = result[0]
        
        cursor.execute("SELECT timestamp FROM schema_snapshots WHERE id = ?", (snapshot2_id,))
        result = cursor.fetchone()
        if not result:
            return []
        snapshot2_time = result[0]
        
        conn.close()
        
        # Get DDL changes from PostgreSQL
        engine = create_engine(f"postgresql://postgres:{quote_plus('Kingkong@1')}@localhost:5432/temp1")
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT event_time, user_name, action, object_type, object_name, command
                FROM ddl_audit_log 
                WHERE event_time > :start_time AND event_time <= :end_time
                ORDER BY event_time
            """), {"start_time": snapshot1_time, "end_time": snapshot2_time})
            
            changes = result.fetchall()
            return [
                {
                    "event_time": str(change[0]),
                    "user_name": change[1] or "Unknown",
                    "action": change[2] or "Unknown",
                    "object_type": change[3] or "Unknown",
                    "object_name": change[4] or "Unknown",
                    "command": (change[5][:100] + "..." if change[5] and len(change[5]) > 100 else change[5]) or "No command"
                }
                for change in changes
            ]
    except Exception as e:
        st.error(f"Error getting DDL changes: {e}")
        return []

def show_enhanced_schema_comparison():
    """Enhanced schema comparison page with user tracking."""
    st.header("Enhanced Schema Comparison")
    st.write("Compare schema snapshots with user attribution")
    
    # Get available snapshots
    conn = sqlite3.connect('data/schema_metadata.db')
    snapshots_df = pd.read_sql_query(
        "SELECT id, timestamp, schema_name FROM schema_snapshots ORDER BY id DESC",
        conn
    )
    conn.close()
    
    # Create snapshot selection
    col1, col2 = st.columns(2)
    
    with col1:
        snapshot1 = st.selectbox(
            "Select First Snapshot (Old)",
            options=snapshots_df['id'].tolist(),
            format_func=lambda x: f"#{x} - {snapshots_df[snapshots_df['id']==x]['timestamp'].iloc[0]}"
        )
    
    with col2:
        snapshot2 = st.selectbox(
            "Select Second Snapshot (New)",
            options=snapshots_df['id'].tolist(),
            format_func=lambda x: f"#{x} - {snapshots_df[snapshots_df['id']==x]['timestamp'].iloc[0]}",
            index=0
        )
    
    if st.button("Compare Schemas with User Tracking", type="primary"):
        if snapshot1 == snapshot2:
            st.warning("Please select different snapshots for comparison.")
            return
        
        # Get DDL changes
        ddl_changes = get_ddl_changes_for_snapshots(snapshot1, snapshot2)
        
        # Get schema diff
        from src.schema_diff import SchemaDiff
        diff_tool = SchemaDiff()
        
        try:
            old_schema = diff_tool.get_snapshot(snapshot1)
            new_schema = diff_tool.get_snapshot(snapshot2)
            changes = diff_tool.compare_schemas(old_schema, new_schema)
            
            # Display DDL changes
            if ddl_changes:
                st.subheader("DDL Changes Detected")
                ddl_df = pd.DataFrame(ddl_changes)
                st.dataframe(ddl_df, use_container_width=True)
                
                # Show user summary
                user_summary = ddl_df['user_name'].value_counts()
                st.write("**Users who made changes:**")
                for user, count in user_summary.items():
                    st.write(f"- **{user}**: {count} changes")
            
            # Display schema changes with user attribution
            if changes:
                st.subheader("Schema Changes Summary")
                
                added = [c for c in changes if c.change_type == "added"]
                removed = [c for c in changes if c.change_type == "removed"]
                modified = [c for c in changes if c.change_type == "modified"]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Added", len(added), delta=len(added))
                with col2:
                    st.metric("Removed", len(removed), delta=-len(removed))
                with col3:
                    st.metric("Modified", len(modified), delta=len(modified))
                
                # Show detailed changes with user attribution
                if modified:
                    st.subheader("🟡 Modified Objects with User Attribution")
                    
                    for change in modified:
                        # Find matching DDL change
                        matching_ddl = None
                        for ddl in ddl_changes:
                            if (ddl['object_name'] == change.parent_object or 
                                ddl['object_name'] == f"public.{change.parent_object}"):
                                matching_ddl = ddl
                                break
                        
                        with st.expander(f"**{change.object_type.title()}:** `{change.object_name}` in `{change.parent_object}`"):
                            st.write(f"**Change:** {change.details}")
                            if change.old_value and change.new_value:
                                st.write(f"**Old Value:** `{change.old_value}`")
                                st.write(f"**New Value:** `{change.new_value}`")
                            
                            if matching_ddl:
                                st.success(f"**Changed by:** {matching_ddl['user_name']} at {matching_ddl['event_time']}")
                                st.code(matching_ddl['command'])
                            else:
                                st.info("User information not available for this change")
                
                if added:
                    st.subheader("🟢 Added Objects")
                    for change in added:
                        st.write(f"- **{change.object_type.title()}:** `{change.object_name}`")
                        if change.parent_object:
                            st.write(f"  (in table `{change.parent_object}`)")
                        st.write(f"  - {change.details}")
                
                if removed:
                    st.subheader("🔴 Removed Objects")
                    for change in removed:
                        st.write(f"- **{change.object_type.title()}:** `{change.object_name}`")
                        if change.parent_object:
                            st.write(f"  (in table `{change.parent_object}`)")
                        st.write(f"  - {change.details}")
            else:
                st.success("No schema changes detected between these snapshots.")
                
        except Exception as e:
            st.error(f"Error comparing schemas: {e}")

def show_dashboard():
    """Show the main dashboard page."""
    st.header("Dashboard")
    st.write("Welcome to the Enhanced PostgreSQL Schema Crawler with User Tracking!")
    
    # Get basic stats
    conn = sqlite3.connect('data/schema_metadata.db')
    snapshots_count = pd.read_sql_query("SELECT COUNT(*) as count FROM schema_snapshots", conn).iloc[0]['count']
    latest_snapshot = pd.read_sql_query("SELECT MAX(timestamp) as latest FROM schema_snapshots", conn).iloc[0]['latest']
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Snapshots", snapshots_count)
    with col2:
        st.metric("Latest Snapshot", latest_snapshot[:19] if latest_snapshot else "None")
    with col3:
        st.metric("User Tracking", "Enabled")
    
    st.subheader("Quick Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Take New Snapshot", type="primary"):
            st.info("Use the Schema Crawler page to take a new snapshot")
    with col2:
        if st.button("Compare Latest", type="secondary"):
            st.info("Use the Enhanced Schema Comparison page to compare snapshots")

def show_schema_crawler():
    """Show the schema crawler page with table filtering."""
    st.header("Schema Crawler")
    st.write("Take new schema snapshots with table filtering")
    
    # Table filtering options
    st.subheader("Table Filtering Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        include_tables = st.text_area(
            "Include Tables (one per line)",
            help="List specific tables to include. Leave empty to include all tables."
        )
        include_patterns = st.text_area(
            "Include Patterns (one per line)",
            help="Pattern matching for table names (supports wildcards like 'user*', 'temp_*')"
        )
    
    with col2:
        exclude_tables = st.text_area(
            "Exclude Tables (one per line)",
            help="List specific tables to exclude"
        )
        exclude_patterns = st.text_area(
            "Exclude Patterns (one per line)",
            help="Pattern matching for table names to exclude (supports wildcards)"
        )
    
    case_sensitive = st.checkbox("Case Sensitive Pattern Matching", value=False)
    
    # Build command
    import sys
    command_parts = [sys.executable, "src/schema_crawler.py", "crawl"]
    
    # Add include tables
    if include_tables.strip():
        tables = [t.strip() for t in include_tables.split('\n') if t.strip()]
        for table in tables:
            command_parts.extend(['--include-tables', table])
    
    # Add exclude tables
    if exclude_tables.strip():
        tables = [t.strip() for t in exclude_tables.split('\n') if t.strip()]
        for table in tables:
            command_parts.extend(['--exclude-tables', table])
    
    # Add include patterns
    if include_patterns.strip():
        patterns = [p.strip() for p in include_patterns.split('\n') if p.strip()]
        for pattern in patterns:
            command_parts.extend(['--include-patterns', pattern])
    
    # Add exclude patterns
    if exclude_patterns.strip():
        patterns = [p.strip() for p in exclude_patterns.split('\n') if p.strip()]
        for pattern in patterns:
            command_parts.extend(['--exclude-patterns', pattern])
    
    # Add case sensitive flag
    if case_sensitive:
        command_parts.append('--case-sensitive')
    
    # Show the command that will be executed
    st.subheader("Command Preview")
    st.code(' '.join(command_parts))
    
    if st.button("Take New Snapshot with Filters", type="primary"):
        try:
            # Import and run the crawler
            import subprocess
            result = subprocess.run(command_parts, capture_output=True, text=True)
            if result.returncode == 0:
                st.success("New snapshot created successfully!")
                st.code(result.stdout)
            else:
                st.error(f"Error creating snapshot: {result.stderr}")
        except Exception as e:
            st.error(f"Error: {e}")
    
    # Show latest schema
    st.subheader("Latest Schema")
    conn = sqlite3.connect('data/schema_metadata.db')
    latest_snapshot = pd.read_sql_query("""
        SELECT id, timestamp, schema_name FROM schema_snapshots 
        ORDER BY timestamp DESC LIMIT 1
    """, conn)
    
    if not latest_snapshot.empty:
        snapshot_id = latest_snapshot.iloc[0]['id']
        st.write(f"**Latest Snapshot ID:** {snapshot_id}")
        st.write(f"**Timestamp:** {latest_snapshot.iloc[0]['timestamp']}")
        
        # Show tables in latest snapshot
        tables_df = pd.read_sql_query("""
            SELECT table_name, table_type, table_owner 
            FROM table_metadata 
            WHERE snapshot_id = ?
        """, conn, params=[snapshot_id])
        
        if not tables_df.empty:
            st.dataframe(tables_df, use_container_width=True)
    conn.close()

def show_schema_history():
    """Show schema history page."""
    st.header("📚 Schema History")
    st.write("View all schema snapshots and their history")
    
    conn = sqlite3.connect('data/schema_metadata.db')
    snapshots_df = pd.read_sql_query("""
        SELECT id, timestamp, schema_name FROM schema_snapshots 
        ORDER BY timestamp DESC
    """, conn)
    conn.close()
    
    if not snapshots_df.empty:
        st.dataframe(snapshots_df, use_container_width=True)
        
        # Show snapshot details
        selected_snapshot = st.selectbox(
            "Select snapshot to view details:",
            options=snapshots_df['id'].tolist(),
            format_func=lambda x: f"#{x} - {snapshots_df[snapshots_df['id']==x]['timestamp'].iloc[0]}"
        )
        
        if selected_snapshot:
            conn = sqlite3.connect('data/schema_metadata.db')
            tables_df = pd.read_sql_query("""
                SELECT table_name, table_type, table_owner 
                FROM table_metadata 
                WHERE snapshot_id = ?
            """, conn, params=[selected_snapshot])
            conn.close()
            
            st.subheader(f"Tables in Snapshot #{selected_snapshot}")
            if not tables_df.empty:
                st.dataframe(tables_df, use_container_width=True)
    else:
        st.info("No snapshots found. Take your first snapshot using the Schema Crawler page.")

def show_settings():
    """Show settings page."""
    st.header("Settings")
    st.write("Configure the schema crawler settings")
    
    st.subheader("Database Configuration")
    st.info("Database settings are configured in config.yaml")
    
    st.subheader("User Tracking")
    st.success("DDL Audit Log Integration: Enabled")
    st.write("The system automatically tracks who made schema changes using PostgreSQL's DDL audit log.")
    
    st.subheader("Storage")
    st.write(f"**Database:** `data/schema_metadata.db`")
    
    # Show database size
    import os
    db_path = "data/schema_metadata.db"
    if os.path.exists(db_path):
        size_kb = os.path.getsize(db_path) / 1024
        st.write(f"**Size:** {size_kb:.1f} KB")

def main():
    st.set_page_config(
        page_title="Enhanced Schema Crawler",
        page_icon=None,
        layout="wide"
    )
    
    st.title("Enhanced PostgreSQL Schema Crawler")
    st.write("Track schema changes with user attribution")
    
    # Navigation
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Dashboard", "Schema Crawler", "Enhanced Schema Comparison", "Schema History", "Settings"]
    )
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Schema Crawler":
        show_schema_crawler()
    elif page == "Enhanced Schema Comparison":
        show_enhanced_schema_comparison()
    elif page == "Schema History":
        show_schema_history()
    elif page == "Settings":
        show_settings()

if __name__ == "__main__":
    main() 