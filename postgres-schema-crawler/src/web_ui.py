"""
Streamlit Web UI for PostgreSQL Schema Crawler

Provides an interactive web interface for viewing schemas and changes.
"""

import streamlit as st
import sqlite3
import json
import pandas as pd
from datetime import datetime
import plotly.express as px
from schema_crawler import DatabaseConnection, SchemaCrawler
from schema_diff import SchemaDiff, diff_schemas

# Page configuration
st.set_page_config(
    page_title="PostgreSQL Schema Crawler",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .change-added { color: #28a745; }
    .change-removed { color: #dc3545; }
    .change-modified { color: #ffc107; }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'current_snapshot' not in st.session_state:
        st.session_state.current_snapshot = None
    if 'db_connected' not in st.session_state:
        st.session_state.db_connected = False


def get_snapshots():
    """Get all saved snapshots from the database."""
    try:
        conn = sqlite3.connect("data/schema_metadata.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, timestamp, schema_name, 
                   (SELECT COUNT(*) FROM table_metadata WHERE snapshot_id = schema_snapshots.id) as table_count
            FROM schema_snapshots 
            ORDER BY timestamp DESC
        """)
        
        snapshots = cursor.fetchall()
        conn.close()
        
        return snapshots
    except Exception as e:
        st.error(f"Error loading snapshots: {e}")
        return []


def get_snapshot_data(snapshot_id):
    """Get detailed data for a specific snapshot."""
    try:
        diff_tool = SchemaDiff()
        return diff_tool.get_snapshot(snapshot_id)
    except Exception as e:
        st.error(f"Error loading snapshot data: {e}")
        return None


def main():
    """Main application function."""
    init_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">PostgreSQL Schema Crawler</h1>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Dashboard", "Schema Crawler", "Schema History", "Schema Comparison", "Settings"]
    )
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Schema Crawler":
        show_schema_crawler()
    elif page == "Schema History":
        show_schema_history()
    elif page == "Schema Comparison":
        show_schema_comparison()
    elif page == "Settings":
        show_settings()


def show_dashboard():
    """Show the main dashboard."""
    st.header("Dashboard")
    
    # Get snapshots
    snapshots = get_snapshots()
    
    if not snapshots:
        st.warning("No schema snapshots found. Run a schema crawl first!")
        return
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Snapshots", len(snapshots))
    
    with col2:
        latest_snapshot = snapshots[0] if snapshots else None
        if latest_snapshot:
            st.metric("Latest Snapshot", f"#{latest_snapshot[0]}")
    
    with col3:
        if latest_snapshot:
            st.metric("Tables in Latest", latest_snapshot[3])
    
    with col4:
        if len(snapshots) >= 2:
            st.metric("Snapshots This Week", len([s for s in snapshots if is_recent(s[1])]))
    
    # Recent activity chart
            st.subheader("Recent Activity")
    
    if len(snapshots) > 1:
        # Create activity data
        activity_data = []
        for i, snapshot in enumerate(snapshots[:10]):  # Last 10 snapshots
            activity_data.append({
                'Date': snapshot[1][:10],
                'Snapshot ID': snapshot[0],
                'Tables': snapshot[3]
            })
        
        df = pd.DataFrame(activity_data)
        fig = px.line(df, x='Date', y='Tables', title='Table Count Over Time')
        st.plotly_chart(fig, use_container_width=True)
    
    # Latest snapshot summary
    if latest_snapshot:
        st.subheader("Latest Schema Summary")
        
        snapshot_data = get_snapshot_data(latest_snapshot[0])
        if snapshot_data:
            # Table summary
            tables_df = pd.DataFrame([
                {
                    'Table': table['table_name'],
                    'Type': table['table_type'],
                    'Owner': table['table_owner'],
                    'Columns': len(table['columns'])
                }
                for table in snapshot_data['tables']
            ])
            
            st.dataframe(tables_df, use_container_width=True)


def show_schema_crawler():
    """Show the schema crawler interface."""
    st.header("Schema Crawler")
    
    # Database connection form
    st.subheader("Database Connection")
    
    with st.form("db_connection"):
        col1, col2 = st.columns(2)
        
        with col1:
            host = st.text_input("Host", value="localhost")
            port = st.number_input("Port", value=5432, min_value=1, max_value=65535)
            database = st.text_input("Database", value="temp1")
        
        with col2:
            user = st.text_input("Username", value="postgres")
            password = st.text_input("Password", value="Kingkong@1", type="password")
            schema = st.text_input("Schema", value="public")
        
        submitted = st.form_submit_button("Connect & Crawl")
        
        if submitted:
            with st.spinner("Connecting to database..."):
                try:
                    # Connect to database
                    db_conn = DatabaseConnection(host, port, database, user, password)
                    if db_conn.connect():
                        st.success("Connected to database successfully!")
                        
                        # Initialize crawler
                        crawler = SchemaCrawler(db_conn, schema)
                        
                        # Crawl schema
                        with st.spinner("Crawling schema..."):
                            schema_data = crawler.crawl_schema()
                            snapshot_id = crawler.save_snapshot(schema_data)
                        
                        st.success(f"Schema crawl completed! Snapshot ID: {snapshot_id}")
                        
                        # Display summary
                        st.subheader("Schema Summary")
                        
                        # Metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Tables", len(schema_data['tables']))
                        with col2:
                            total_columns = sum(len(table['columns']) for table in schema_data['tables'])
                            st.metric("Total Columns", total_columns)
                        with col3:
                            st.metric("Snapshot ID", snapshot_id)
                        
                        # Table details
                        if schema_data['tables']:
                            st.subheader("Table Details")
                            
                            # Create expandable sections for each table
                            for table in schema_data['tables']:
                                with st.expander(f"Table: {table['table_name']} ({len(table['columns'])} columns)"):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.write(f"**Type:** {table['table_type']}")
                                        st.write(f"**Owner:** {table['table_owner']}")
                                    
                                    with col2:
                                        st.write(f"**Columns:** {len(table['columns'])}")
                                        if table['constraints']:
                                            st.write(f"**Constraints:** {len(table['constraints'])}")
                                    
                                    # Column table
                                    if table['columns']:
                                        columns_df = pd.DataFrame([
                                            {
                                                'Column': col['column_name'],
                                                'Type': col['data_type'],
                                                'Nullable': col['is_nullable'],
                                                'Default': col['column_default'] or 'NULL',
                                                'Position': col['ordinal_position']
                                            }
                                            for col in table['columns']
                                        ])
                                        st.dataframe(columns_df, use_container_width=True)
                        
                        db_conn.disconnect()
                    else:
                        st.error("Failed to connect to database")
                        
                except Exception as e:
                    st.error(f"Error: {e}")


def show_schema_history():
    """Show schema history and snapshots."""
    st.header("📚 Schema History")
    
    snapshots = get_snapshots()
    
    if not snapshots:
        st.warning("No schema snapshots found.")
        return
    
    # Snapshot selector
    st.subheader("Select Snapshot")
    
    snapshot_options = {f"#{s[0]} - {s[1]} ({s[3]} tables)": s[0] for s in snapshots}
    selected_snapshot = st.selectbox("Choose a snapshot:", list(snapshot_options.keys()))
    
    if selected_snapshot:
        snapshot_id = snapshot_options[selected_snapshot]
        snapshot_data = get_snapshot_data(snapshot_id)
        
        if snapshot_data:
            st.subheader(f"Schema Details - Snapshot #{snapshot_id}")
            
            # Export options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📄 Export as JSON"):
                    json_str = json.dumps(snapshot_data, indent=2)
                    st.download_button(
                        label="Download JSON",
                        data=json_str,
                        file_name=f"schema_snapshot_{snapshot_id}.json",
                        mime="application/json"
                    )
            
            with col2:
                if st.button("Export as CSV"):
                    # Convert to CSV format
                    tables_data = []
                    for table in snapshot_data['tables']:
                        for col in table['columns']:
                            tables_data.append({
                                'table_name': table['table_name'],
                                'table_type': table['table_type'],
                                'table_owner': table['table_owner'],
                                'column_name': col['column_name'],
                                'data_type': col['data_type'],
                                'is_nullable': col['is_nullable'],
                                'column_default': col['column_default'],
                                'ordinal_position': col['ordinal_position']
                            })
                    
                    df = pd.DataFrame(tables_data)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"schema_snapshot_{snapshot_id}.csv",
                        mime="text/csv"
                    )
            
            with col3:
                if st.button("Export as Markdown"):
                    markdown_content = generate_markdown_report(snapshot_data)
                    st.download_button(
                        label="Download Markdown",
                        data=markdown_content,
                        file_name=f"schema_snapshot_{snapshot_id}.md",
                        mime="text/markdown"
                    )
            
            # Schema visualization
            st.subheader("Schema Visualization")
            
            # Table count by type
            table_types = {}
            for table in snapshot_data['tables']:
                table_type = table['table_type']
                table_types[table_type] = table_types.get(table_type, 0) + 1
            
            if table_types:
                fig = px.pie(
                    values=list(table_types.values()),
                    names=list(table_types.keys()),
                    title="Tables by Type"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Column count by data type
            data_types = {}
            for table in snapshot_data['tables']:
                for col in table['columns']:
                    data_type = col['data_type']
                    data_types[data_type] = data_types.get(data_type, 0) + 1
            
            if data_types:
                # Show top 10 data types
                top_types = dict(sorted(data_types.items(), key=lambda x: x[1], reverse=True)[:10])
                
                fig = px.bar(
                    x=list(top_types.keys()),
                    y=list(top_types.values()),
                    title="Top 10 Data Types"
                )
                st.plotly_chart(fig, use_container_width=True)


def show_schema_comparison():
    """Show schema comparison interface."""
    st.header("Schema Comparison")
    
    snapshots = get_snapshots()
    
    if len(snapshots) < 2:
        st.warning("Need at least 2 snapshots to compare.")
        return
    
    # Snapshot selection
    st.subheader("Select Snapshots to Compare")
    
    col1, col2 = st.columns(2)
    
    with col1:
        snapshot_options = {f"#{s[0]} - {s[1]}": s[0] for s in snapshots}
        old_snapshot = st.selectbox("Older Snapshot:", list(snapshot_options.keys()))
    
    with col2:
        new_snapshot = st.selectbox("Newer Snapshot:", list(snapshot_options.keys()))
    
    if old_snapshot and new_snapshot and old_snapshot != new_snapshot:
        if st.button("Compare Schemas"):
            old_id = snapshot_options[old_snapshot]
            new_id = snapshot_options[new_snapshot]
            
            with st.spinner("Comparing schemas..."):
                try:
                    changes = diff_schemas(old_id, new_id)
                    
                    if changes:
                        st.subheader("Changes Detected")
                        
                        # Summary metrics
                        added = [c for c in changes if c.change_type == "added"]
                        removed = [c for c in changes if c.change_type == "removed"]
                        modified = [c for c in changes if c.change_type == "modified"]
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Added", len(added), delta=len(added))
                        with col2:
                            st.metric("Removed", len(removed), delta=-len(removed))
                        with col3:
                            st.metric("Modified", len(modified))
                        
                        # Detailed changes
                        st.subheader("Detailed Changes")
                        
                        # Added objects
                        if added:
                            st.write("🟢 **Added Objects:**")
                            added_df = pd.DataFrame([
                                {
                                    'Type': change.object_type.title(),
                                    'Name': change.object_name,
                                    'Parent': change.parent_object or '-',
                                    'Details': change.details
                                }
                                for change in added
                            ])
                            st.dataframe(added_df, use_container_width=True)
                        
                        # Removed objects
                        if removed:
                            st.write("🔴 **Removed Objects:**")
                            removed_df = pd.DataFrame([
                                {
                                    'Type': change.object_type.title(),
                                    'Name': change.object_name,
                                    'Parent': change.parent_object or '-',
                                    'Details': change.details
                                }
                                for change in removed
                            ])
                            st.dataframe(removed_df, use_container_width=True)
                        
                        # Modified objects
                        if modified:
                            st.write("🟡 **Modified Objects:**")
                            modified_df = pd.DataFrame([
                                {
                                    'Type': change.object_type.title(),
                                    'Name': change.object_name,
                                    'Parent': change.parent_object or '-',
                                    'Old Value': change.old_value,
                                    'New Value': change.new_value,
                                    'Details': change.details
                                }
                                for change in modified
                            ])
                            st.dataframe(modified_df, use_container_width=True)
                        
                        # Export comparison report
                        if st.button("📄 Export Comparison Report"):
                            diff_tool = SchemaDiff()
                            report = diff_tool.generate_diff_report(changes, old_id, new_id)
                            st.download_button(
                                label="Download Report",
                                data=report,
                                file_name=f"schema_comparison_{old_id}_to_{new_id}.md",
                                mime="text/markdown"
                            )
                    else:
                        st.success("No changes detected between the selected snapshots.")
                        
                except Exception as e:
                    st.error(f"Error comparing schemas: {e}")


def show_settings():
    """Show application settings."""
    st.header("⚙️ Settings")
    
    st.subheader("Database Configuration")
    
    # Load current config
    try:
        import yaml
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
    except:
        config = {}
    
    with st.form("settings_form"):
        st.write("**Database Settings**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            host = st.text_input("Host", value=config.get('database', {}).get('host', 'localhost'))
            port = st.number_input("Port", value=config.get('database', {}).get('port', 5432))
            database = st.text_input("Database", value=config.get('database', {}).get('name', 'temp1'))
        
        with col2:
            user = st.text_input("Username", value=config.get('database', {}).get('user', 'postgres'))
            password = st.text_input("Password", value=config.get('database', {}).get('password', ''), type="password")
            schema = st.text_input("Schema", value=config.get('database', {}).get('schema', 'public'))
        
        st.write("**Crawler Settings**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            include_constraints = st.checkbox("Include Constraints", value=config.get('crawler', {}).get('include_constraints', True))
            include_indexes = st.checkbox("Include Indexes", value=config.get('crawler', {}).get('include_indexes', False))
        
        with col2:
            max_tables = st.number_input("Max Tables (0 = unlimited)", value=config.get('crawler', {}).get('max_tables', 0), min_value=0)
            export_format = st.selectbox("Default Export Format", ['json', 'csv', 'markdown'], 
                                       index=['json', 'csv', 'markdown'].index(config.get('output', {}).get('export_format', 'json')))
        
        submitted = st.form_submit_button("Save Settings")
        
        if submitted:
            # Update config
            config['database'] = {
                'host': host,
                'port': port,
                'name': database,
                'user': user,
                'password': password,
                'schema': schema
            }
            
            config['crawler'] = {
                'include_constraints': include_constraints,
                'include_indexes': include_indexes,
                'max_tables': max_tables
            }
            
            config['output'] = {
                'export_format': export_format
            }
            
            # Save config
            try:
                with open("config.yaml", "w") as f:
                    yaml.dump(config, f, default_flow_style=False)
                st.success("Settings saved successfully!")
            except Exception as e:
                st.error(f"Error saving settings: {e}")


def is_recent(timestamp_str, days=7):
    """Check if a timestamp is within the last N days."""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now()
        return (now - timestamp).days <= days
    except:
        return False


def generate_markdown_report(schema_data):
    """Generate a markdown report from schema data."""
    report = []
    report.append(f"# Schema Report - {schema_data['schema_name']}\n")
    report.append(f"**Generated:** {schema_data['crawl_timestamp']}\n")
    report.append(f"**Total Tables:** {len(schema_data['tables'])}\n\n")
    
    for table in schema_data['tables']:
        report.append(f"## Table: {table['table_name']}\n")
        report.append(f"- **Type:** {table['table_type']}")
        report.append(f"- **Owner:** {table['table_owner']}")
        report.append(f"- **Columns:** {len(table['columns'])}\n")
        
        if table['columns']:
            report.append("| Column | Type | Nullable | Default | Position |")
            report.append("|--------|------|----------|---------|----------|")
            
            for col in table['columns']:
                default = col['column_default'] or 'NULL'
                report.append(f"| {col['column_name']} | {col['data_type']} | {col['is_nullable']} | {default} | {col['ordinal_position']} |")
        
        report.append("\n")
    
    return "\n".join(report)


if __name__ == "__main__":
    main() 