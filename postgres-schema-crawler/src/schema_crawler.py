"""
PostgreSQL Schema Crawler

A lightweight tool to crawl and track PostgreSQL schema changes over time.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Result
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import click
from schema_diff import SchemaDiff, diff_schemas

console = Console()


class DatabaseConnection:
    """Handles PostgreSQL database connections."""
    
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
    
    def connect(self):
        """Establish database connection."""
        try:
            from urllib.parse import quote_plus
            # URL-encode the password to handle special characters
            encoded_password = quote_plus(self.password)
            connection_string = f"postgresql://{self.user}:{encoded_password}@{self.host}:{self.port}/{self.database}"
            self.connection = create_engine(connection_string)
            # Test connection
            with self.connection.connect() as conn:
                conn.execute(text("SELECT 1"))
            console.print(f"[green]Connected to PostgreSQL database: {self.database}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Failed to connect to database: {e}[/red]")
            return False
    
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.dispose()
            console.print("[yellow]Database connection closed[/yellow]")
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a query and return results as list of dictionaries."""
        if not self.connection:
            raise Exception("Database not connected")
        
        with self.connection.connect() as conn:
            result = conn.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]


class SchemaCrawler:
    """Main schema crawler class."""
    
    def __init__(self, db_connection: DatabaseConnection, schema: str = "public", table_filter: Dict = None):
        self.db = db_connection
        self.schema = schema
        self.metadata_db_path = "data/schema_metadata.db"
        self.table_filter = table_filter or {}
        self._init_metadata_db()
    
    def _init_metadata_db(self):
        """Initialize SQLite database for storing schema metadata."""
        os.makedirs("data", exist_ok=True)
        
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        # Create tables for storing schema snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                schema_name TEXT NOT NULL,
                snapshot_data TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS table_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER,
                table_name TEXT NOT NULL,
                table_type TEXT,
                table_owner TEXT,
                table_comment TEXT,
                FOREIGN KEY (snapshot_id) REFERENCES schema_snapshots (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS column_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_id INTEGER,
                column_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                is_nullable BOOLEAN,
                column_default TEXT,
                ordinal_position INTEGER,
                column_comment TEXT,
                FOREIGN KEY (table_id) REFERENCES table_metadata (id)
            )
        """)
        
        conn.commit()
        conn.close()
        console.print(f"[blue]Metadata database initialized: {self.metadata_db_path}[/blue]")
    
    def _should_include_table(self, table_name: str) -> bool:
        """Check if a table should be included based on filter settings."""
        import fnmatch
        
        # Convert to lowercase if case-insensitive
        check_name = table_name.lower() if not self.table_filter.get('case_sensitive', False) else table_name
        
        # Check include_tables (if specified, table must be in this list)
        include_tables = self.table_filter.get('include_tables', [])
        if include_tables:
            check_include = [t.lower() if not self.table_filter.get('case_sensitive', False) else t for t in include_tables]
            if check_name not in check_include:
                return False
        
        # Check exclude_tables
        exclude_tables = self.table_filter.get('exclude_tables', [])
        if exclude_tables:
            check_exclude = [t.lower() if not self.table_filter.get('case_sensitive', False) else t for t in exclude_tables]
            if check_name in check_exclude:
                return False
        
        # Check include_patterns
        include_patterns = self.table_filter.get('include_patterns', [])
        if include_patterns:
            if not any(fnmatch.fnmatch(check_name, pattern) for pattern in include_patterns):
                return False
        
        # Check exclude_patterns
        exclude_patterns = self.table_filter.get('exclude_patterns', [])
        if exclude_patterns:
            if any(fnmatch.fnmatch(check_name, pattern) for pattern in exclude_patterns):
                return False
        
        return True
    
    def get_tables(self) -> List[Dict]:
        """Get all tables in the specified schema."""
        query = """
            SELECT 
                t.table_name,
                t.table_type,
                COALESCE(c.relowner::regrole::text, 'unknown') as table_owner
            FROM information_schema.tables t
            LEFT JOIN pg_class c ON c.relname = t.table_name
            LEFT JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
            WHERE t.table_schema = :schema
            ORDER BY t.table_name
        """
        
        all_tables = self.db.execute_query(query, {"schema": self.schema})
        
        # Apply table filtering
        if self.table_filter:
            filtered_tables = []
            for table in all_tables:
                if self._should_include_table(table["table_name"]):
                    filtered_tables.append(table)
                else:
                    console.print(f"  [yellow]Skipping table (filtered): {table['table_name']}[/yellow]")
            return filtered_tables
        
        return all_tables
    
    def get_table_columns(self, table_name: str) -> List[Dict]:
        """Get column metadata for a specific table."""
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                ordinal_position,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                datetime_precision
            FROM information_schema.columns 
            WHERE table_schema = :schema AND table_name = :table_name
            ORDER BY ordinal_position
        """
        
        return self.db.execute_query(query, {"schema": self.schema, "table_name": table_name})
    
    def get_table_constraints(self, table_name: str) -> List[Dict]:
        """Get constraint information for a table."""
        query = """
            SELECT 
                tc.constraint_name,
                tc.constraint_type,
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_schema = :schema 
                AND tc.table_name = :table_name
            ORDER BY tc.constraint_name, kcu.ordinal_position
        """
        
        return self.db.execute_query(query, {"schema": self.schema, "table_name": table_name})
    
    def crawl_schema(self) -> Dict:
        """Crawl the entire schema and return structured metadata."""
        console.print(f"[blue]Crawling schema: {self.schema}[/blue]")
        
        tables = self.get_tables()
        schema_data = {
            "schema_name": self.schema,
            "crawl_timestamp": datetime.now().isoformat(),
            "tables": []
        }
        
        for table in tables:
            table_name = table["table_name"]
            console.print(f"  [cyan]Processing table: {table_name}[/cyan]")
            
            columns = self.get_table_columns(table_name)
            constraints = self.get_table_constraints(table_name)
            
            table_data = {
                "table_name": table_name,
                "table_type": table["table_type"],
                "table_owner": table["table_owner"],
                "columns": [dict(col) for col in columns],
                "constraints": [dict(con) for con in constraints]
            }
            
            schema_data["tables"].append(table_data)
        
        console.print(f"[green]Schema crawl completed. Found {len(tables)} tables[/green]")
        return schema_data
    
    def save_snapshot(self, schema_data: Dict) -> int:
        """Save schema snapshot to SQLite database."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        # Save main snapshot
        cursor.execute("""
            INSERT INTO schema_snapshots (timestamp, schema_name, snapshot_data)
            VALUES (?, ?, ?)
        """, (
            schema_data["crawl_timestamp"],
            schema_data["schema_name"],
            json.dumps(schema_data)
        ))
        
        snapshot_id = cursor.lastrowid
        
        # Save table metadata
        for table in schema_data["tables"]:
            cursor.execute("""
                INSERT INTO table_metadata (snapshot_id, table_name, table_type, table_owner, table_comment)
                VALUES (?, ?, ?, ?, ?)
            """, (
                snapshot_id,
                table["table_name"],
                table["table_type"],
                table["table_owner"],
                table.get("table_comment", "")
            ))
            
            table_id = cursor.lastrowid
            
            # Save column metadata
            for column in table["columns"]:
                cursor.execute("""
                    INSERT INTO column_metadata 
                    (table_id, column_name, data_type, is_nullable, column_default, ordinal_position, column_comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    table_id,
                    column["column_name"],
                    column["data_type"],
                    column["is_nullable"] == "YES",
                    column["column_default"],
                    column["ordinal_position"],
                    column.get("column_comment", "")
                ))
        
        conn.commit()
        conn.close()
        
        console.print(f"[green]Snapshot saved with ID: {snapshot_id}[/green]")
        return snapshot_id
    
    def display_schema_summary(self, schema_data: Dict):
        """Display a rich summary of the schema."""
        table = Table(title=f"Schema Summary - {self.schema}")
        table.add_column("Table Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Owner", style="yellow")
        table.add_column("Columns", style="green")
        
        for table_data in schema_data["tables"]:
            table.add_row(
                table_data["table_name"],
                table_data["table_type"],
                table_data["table_owner"],
                str(len(table_data["columns"]))
            )
        
        console.print(table)
        
        # Show detailed column info for first few tables
        for i, table_data in enumerate(schema_data["tables"][:3]):
            console.print(f"\n[bold cyan]Table: {table_data['table_name']}[/bold cyan]")
            
            col_table = Table(show_header=True, header_style="bold magenta")
            col_table.add_column("Column")
            col_table.add_column("Type")
            col_table.add_column("Nullable")
            col_table.add_column("Default")
            
            for col in table_data["columns"]:
                col_table.add_row(
                    col["column_name"],
                    col["data_type"],
                    "YES" if col["is_nullable"] == "YES" else "NO",
                    str(col["column_default"]) if col["column_default"] else "NULL"
                )
            
            console.print(col_table)


@click.group()
def cli():
    """PostgreSQL Schema Crawler CLI"""
    pass


@cli.command()
@click.option('--host', default='localhost', help='Database host')
@click.option('--port', default=5432, help='Database port')
@click.option('--database', default='temp1', help='Database name')
@click.option('--user', default='postgres', help='Database user')
@click.option('--password', default='Kingkong@1', help='Database password')
@click.option('--schema', default='public', help='Schema to crawl')
@click.option('--include-tables', multiple=True, help='Specific tables to include (can be used multiple times)')
@click.option('--exclude-tables', multiple=True, help='Tables to exclude (can be used multiple times)')
@click.option('--include-patterns', multiple=True, help='Pattern to include tables (supports wildcards, can be used multiple times)')
@click.option('--exclude-patterns', multiple=True, help='Pattern to exclude tables (supports wildcards, can be used multiple times)')
@click.option('--case-sensitive', is_flag=True, help='Case sensitive pattern matching')
def crawl(host, port, database, user, password, schema, include_tables, exclude_tables, include_patterns, exclude_patterns, case_sensitive):
    """Crawl and save schema snapshot."""
    console.print(Panel.fit("PostgreSQL Schema Crawler", style="bold blue"))
    
    # Build table filter configuration
    table_filter = {}
    if include_tables:
        table_filter['include_tables'] = list(include_tables)
    if exclude_tables:
        table_filter['exclude_tables'] = list(exclude_tables)
    if include_patterns:
        table_filter['include_patterns'] = list(include_patterns)
    if exclude_patterns:
        table_filter['exclude_patterns'] = list(exclude_patterns)
    if case_sensitive:
        table_filter['case_sensitive'] = case_sensitive
    
    # Display filter information
    if table_filter:
        console.print("[blue]Table filtering enabled:[/blue]")
        for key, value in table_filter.items():
            console.print(f"  [cyan]{key}:[/cyan] {value}")
        console.print()
    
    # Connect to database
    db_conn = DatabaseConnection(host, port, database, user, password)
    if not db_conn.connect():
        return
    
    try:
        # Initialize crawler with table filter
        crawler = SchemaCrawler(db_conn, schema, table_filter)
        
        # Crawl schema
        schema_data = crawler.crawl_schema()
        
        # Save snapshot
        snapshot_id = crawler.save_snapshot(schema_data)
        
        # Display summary
        crawler.display_schema_summary(schema_data)
        
        console.print(f"\n[bold green]Schema crawl completed successfully![/bold green]")
        console.print(f"[blue]Snapshot ID: {snapshot_id}[/blue]")
        
    finally:
        db_conn.disconnect()


@cli.command()
def list_snapshots():
    """List all saved schema snapshots."""
    if not os.path.exists("data/schema_metadata.db"):
        console.print("[red]No schema metadata database found. Run a crawl first.[/red]")
        return
    
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
    
    if not snapshots:
        console.print("No snapshots found.", style="yellow")
        return
    
    table = Table(title="Schema Snapshots")
    table.add_column("ID", style="cyan")
    table.add_column("Timestamp", style="green")
    table.add_column("Schema", style="magenta")
    table.add_column("Tables", style="yellow")
    
    for snapshot in snapshots:
        table.add_row(str(snapshot[0]), snapshot[1], snapshot[2], str(snapshot[3]))
    
    console.print(table)


@cli.command()
@click.argument('snapshot1', type=int)
@click.argument('snapshot2', type=int)
@click.option('--output', '-o', help='Output file for the diff report')
def diff(snapshot1, snapshot2, output):
    """Compare two schema snapshots."""
    diff_schemas(snapshot1, snapshot2, output)


@cli.command()
@click.option('--output', '-o', help='Output file for the diff report')
def diff_latest(output):
    """Compare the two most recent schema snapshots."""
    if not os.path.exists("data/schema_metadata.db"):
        console.print("[red]No schema metadata database found. Run a crawl first.[/red]")
        return
    
    diff_tool = SchemaDiff()
    snapshots = diff_tool.get_latest_snapshots(2)
    
    if len(snapshots) < 2:
        console.print("[red]Need at least 2 snapshots to compare.[/red]")
        return
    
    snapshot1_id, _ = snapshots[1]  # Older snapshot
    snapshot2_id, _ = snapshots[0]  # Newer snapshot
    
    console.print(f"[blue]Comparing latest snapshots: {snapshot1_id} → {snapshot2_id}[/blue]")
    diff_schemas(snapshot1_id, snapshot2_id, output)


@cli.command()
@click.argument('snapshot_id', type=int)
@click.option('--format', '-f', default='json', type=click.Choice(['json', 'csv', 'markdown']), help='Export format')
@click.option('--output', '-o', help='Output file')
def export(snapshot_id, format, output):
    """Export a schema snapshot to various formats."""
    if not os.path.exists("data/schema_metadata.db"):
        console.print("[red]No schema metadata database found. Run a crawl first.[/red]")
        return
    
    diff_tool = SchemaDiff()
    
    try:
        schema_data = diff_tool.get_snapshot(snapshot_id)
        
        if format == 'json':
            content = json.dumps(schema_data, indent=2)
            extension = '.json'
        elif format == 'csv':
            # Convert to CSV format
            import pandas as pd
            tables_data = []
            for table in schema_data['tables']:
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
            content = df.to_csv(index=False)
            extension = '.csv'
        elif format == 'markdown':
            content = generate_markdown_report(schema_data)
            extension = '.md'
        
        if output:
            filename = output
        else:
            filename = f"data/schema_snapshot_{snapshot_id}{extension}"
        
        with open(filename, 'w') as f:
            f.write(content)
        
        console.print(f"[green]Schema exported to: {filename}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error exporting schema: {e}[/red]")


def generate_markdown_report(schema_data: Dict) -> str:
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
    cli()
