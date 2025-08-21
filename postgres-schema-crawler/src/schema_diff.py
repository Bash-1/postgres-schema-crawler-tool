"""
Schema Diffing Module

Compares two schema snapshots and detects changes between them.
"""

import json
from datetime import datetime
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import sqlite3

console = Console()


@dataclass
class SchemaChange:
    """Represents a single schema change."""
    change_type: str  # 'added', 'removed', 'modified'
    object_type: str  # 'table', 'column', 'constraint'
    object_name: str
    parent_object: str = None
    old_value: Any = None
    new_value: Any = None
    details: str = ""


class SchemaDiff:
    """Handles schema comparison and change detection."""
    
    def __init__(self, metadata_db_path: str = "data/schema_metadata.db"):
        self.metadata_db_path = metadata_db_path
    
    def get_snapshot(self, snapshot_id: int) -> Dict:
        """Retrieve a schema snapshot by ID."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT snapshot_data FROM schema_snapshots WHERE id = ?
        """, (snapshot_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        return json.loads(result[0])
    
    def get_latest_snapshots(self, count: int = 2) -> List[Tuple[int, Dict]]:
        """Get the latest schema snapshots."""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, snapshot_data FROM schema_snapshots 
            ORDER BY timestamp DESC LIMIT ?
        """, (count,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [(row[0], json.loads(row[1])) for row in results]
    
    def compare_schemas(self, old_schema: Dict, new_schema: Dict) -> List[SchemaChange]:
        """Compare two schema snapshots and return list of changes."""
        changes = []
        
        # Get table names from both schemas
        old_tables = {table["table_name"]: table for table in old_schema["tables"]}
        new_tables = {table["table_name"]: table for table in new_schema["tables"]}
        
        # Find added tables
        for table_name in new_tables:
            if table_name not in old_tables:
                changes.append(SchemaChange(
                    change_type="added",
                    object_type="table",
                    object_name=table_name,
                    details=f"Table '{table_name}' was added"
                ))
        
        # Find removed tables
        for table_name in old_tables:
            if table_name not in new_tables:
                changes.append(SchemaChange(
                    change_type="removed",
                    object_type="table",
                    object_name=table_name,
                    details=f"Table '{table_name}' was removed"
                ))
        
        # Compare existing tables
        for table_name in old_tables:
            if table_name in new_tables:
                table_changes = self._compare_table(
                    old_tables[table_name], 
                    new_tables[table_name]
                )
                changes.extend(table_changes)
        
        return changes
    
    def _compare_table(self, old_table: Dict, new_table: Dict) -> List[SchemaChange]:
        """Compare two table definitions and return changes."""
        changes = []
        table_name = old_table["table_name"]
        
        # Compare table properties
        if old_table["table_type"] != new_table["table_type"]:
            changes.append(SchemaChange(
                change_type="modified",
                object_type="table",
                object_name=table_name,
                old_value=old_table["table_type"],
                new_value=new_table["table_type"],
                details=f"Table type changed from '{old_table['table_type']}' to '{new_table['table_type']}'"
            ))
        
        if old_table["table_owner"] != new_table["table_owner"]:
            changes.append(SchemaChange(
                change_type="modified",
                object_type="table",
                object_name=table_name,
                old_value=old_table["table_owner"],
                new_value=new_table["table_owner"],
                details=f"Table owner changed from '{old_table['table_owner']}' to '{new_table['table_owner']}'"
            ))
        
        # Compare columns
        old_columns = {col["column_name"]: col for col in old_table["columns"]}
        new_columns = {col["column_name"]: col for col in new_table["columns"]}
        
        # Find added columns
        for col_name in new_columns:
            if col_name not in old_columns:
                changes.append(SchemaChange(
                    change_type="added",
                    object_type="column",
                    object_name=col_name,
                    parent_object=table_name,
                    details=f"Column '{col_name}' was added to table '{table_name}'"
                ))
        
        # Find removed columns
        for col_name in old_columns:
            if col_name not in new_columns:
                changes.append(SchemaChange(
                    change_type="removed",
                    object_type="column",
                    object_name=col_name,
                    parent_object=table_name,
                    details=f"Column '{col_name}' was removed from table '{table_name}'"
                ))
        
        # Compare existing columns
        for col_name in old_columns:
            if col_name in new_columns:
                col_changes = self._compare_column(
                    old_columns[col_name], 
                    new_columns[col_name], 
                    table_name
                )
                changes.extend(col_changes)
        
        return changes
    
    def _compare_column(self, old_col: Dict, new_col: Dict, table_name: str) -> List[SchemaChange]:
        """Compare two column definitions and return changes."""
        changes = []
        col_name = old_col["column_name"]
        
        # Compare data type
        if old_col["data_type"] != new_col["data_type"]:
            changes.append(SchemaChange(
                change_type="modified",
                object_type="column",
                object_name=col_name,
                parent_object=table_name,
                old_value=old_col["data_type"],
                new_value=new_col["data_type"],
                details=f"Column '{col_name}' data type changed from '{old_col['data_type']}' to '{new_col['data_type']}'"
            ))
        
        # Compare nullability
        if old_col["is_nullable"] != new_col["is_nullable"]:
            changes.append(SchemaChange(
                change_type="modified",
                object_type="column",
                object_name=col_name,
                parent_object=table_name,
                old_value=old_col["is_nullable"],
                new_value=new_col["is_nullable"],
                details=f"Column '{col_name}' nullability changed from '{old_col['is_nullable']}' to '{new_col['is_nullable']}'"
            ))
        
        # Compare default values
        old_default = old_col.get("column_default")
        new_default = new_col.get("column_default")
        if old_default != new_default:
            changes.append(SchemaChange(
                change_type="modified",
                object_type="column",
                object_name=col_name,
                parent_object=table_name,
                old_value=old_default,
                new_value=new_default,
                details=f"Column '{col_name}' default value changed from '{old_default}' to '{new_default}'"
            ))
        
        # Compare character maximum length
        old_length = old_col.get("character_maximum_length")
        new_length = new_col.get("character_maximum_length")
        if old_length != new_length:
            changes.append(SchemaChange(
                change_type="modified",
                object_type="column",
                object_name=col_name,
                parent_object=table_name,
                old_value=f"VARCHAR({old_length})" if old_length else old_col["data_type"],
                new_value=f"VARCHAR({new_length})" if new_length else new_col["data_type"],
                details=f"Column '{col_name}' character length changed from {old_length} to {new_length}"
            ))
        
        # Compare ordinal position
        if old_col["ordinal_position"] != new_col["ordinal_position"]:
            changes.append(SchemaChange(
                change_type="modified",
                object_type="column",
                object_name=col_name,
                parent_object=table_name,
                old_value=old_col["ordinal_position"],
                new_value=new_col["ordinal_position"],
                details=f"Column '{col_name}' position changed from {old_col['ordinal_position']} to {new_col['ordinal_position']}"
            ))
        
        return changes
    
    def generate_diff_report(self, changes: List[SchemaChange], 
                           old_snapshot_id: int = None, 
                           new_snapshot_id: int = None) -> str:
        """Generate a markdown report of schema changes."""
        report = []
        report.append("# Schema Change Report\n")
        
        if old_snapshot_id and new_snapshot_id:
            report.append(f"**Comparing snapshots:** {old_snapshot_id} → {new_snapshot_id}\n")
        
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"**Total changes:** {len(changes)}\n\n")
        
        if not changes:
            report.append("No changes detected between schemas.\n")
            return "\n".join(report)
        
        # Group changes by type
        added = [c for c in changes if c.change_type == "added"]
        removed = [c for c in changes if c.change_type == "removed"]
        modified = [c for c in changes if c.change_type == "modified"]
        
        # Summary
        report.append("## Summary\n")
        report.append(f"- **Added:** {len(added)} objects\n")
        report.append(f"- **Removed:** {len(removed)} objects\n")
        report.append(f"- **Modified:** {len(modified)} objects\n\n")
        
        # Added objects
        if added:
            report.append("## Added Objects\n")
            for change in added:
                report.append(f"- **{change.object_type.title()}:** `{change.object_name}`")
                if change.parent_object:
                    report.append(f"  (in table `{change.parent_object}`)")
                report.append(f"  - {change.details}\n")
        
        # Removed objects
        if removed:
            report.append("## Removed Objects\n")
            for change in removed:
                report.append(f"- **{change.object_type.title()}:** `{change.object_name}`")
                if change.parent_object:
                    report.append(f"  (in table `{change.parent_object}`)")
                report.append(f"  - {change.details}\n")
        
        # Modified objects
        if modified:
            report.append("## Modified Objects\n")
            for change in modified:
                report.append(f"- **{change.object_type.title()}:** `{change.object_name}`")
                if change.parent_object:
                    report.append(f"  (in table `{change.parent_object}`)")
                report.append(f"  - {change.details}")
                if change.old_value and change.new_value:
                    report.append(f"    - Old: `{change.old_value}`")
                    report.append(f"    - New: `{change.new_value}`")
                report.append("")
        
        return "\n".join(report)
    
    def display_changes(self, changes: List[SchemaChange]):
        """Display changes in a rich table format."""
        if not changes:
            console.print("No changes detected between schemas.", style="green")
            return
        
        # Group changes by type
        added = [c for c in changes if c.change_type == "added"]
        removed = [c for c in changes if c.change_type == "removed"]
        modified = [c for c in changes if c.change_type == "modified"]
        
        console.print(f"\nSchema Changes Summary:", style="bold blue")
        console.print(f"  Added: {len(added)} | Removed: {len(removed)} | Modified: {len(modified)}")
        
        # Display added objects
        if added:
            console.print(f"\n🟢 Added Objects ({len(added)}):", style="bold green")
            table = Table(show_header=True, header_style="bold green")
            table.add_column("Type")
            table.add_column("Name")
            table.add_column("Parent")
            table.add_column("Details")
            
            for change in added:
                table.add_row(
                    change.object_type.title(),
                    change.object_name,
                    change.parent_object or "-",
                    change.details[:50] + "..." if len(change.details) > 50 else change.details
                )
            console.print(table)
        
        # Display removed objects
        if removed:
            console.print(f"\n🔴 Removed Objects ({len(removed)}):", style="bold red")
            table = Table(show_header=True, header_style="bold red")
            table.add_column("Type")
            table.add_column("Name")
            table.add_column("Parent")
            table.add_column("Details")
            
            for change in removed:
                table.add_row(
                    change.object_type.title(),
                    change.object_name,
                    change.parent_object or "-",
                    change.details[:50] + "..." if len(change.details) > 50 else change.details
                )
            console.print(table)
        
        # Display modified objects
        if modified:
            console.print(f"\n🟡 Modified Objects ({len(modified)}):", style="bold yellow")
            table = Table(show_header=True, header_style="bold yellow")
            table.add_column("Type")
            table.add_column("Name")
            table.add_column("Parent")
            table.add_column("Change")
            
            for change in modified:
                change_text = f"{change.old_value} → {change.new_value}" if change.old_value and change.new_value else change.details
                table.add_row(
                    change.object_type.title(),
                    change.object_name,
                    change.parent_object or "-",
                    change_text[:40] + "..." if len(change_text) > 40 else change_text
                )
            console.print(table)


def diff_schemas(snapshot1_id: int, snapshot2_id: int, output_file: str = None) -> List[SchemaChange]:
    """Compare two schema snapshots and return changes."""
    diff_tool = SchemaDiff()
    
    try:
        # Get snapshots
        old_schema = diff_tool.get_snapshot(snapshot1_id)
        new_schema = diff_tool.get_snapshot(snapshot2_id)
        
        console.print(f"Comparing snapshots {snapshot1_id} and {snapshot2_id}...", style="blue")
        
        # Compare schemas
        changes = diff_tool.compare_schemas(old_schema, new_schema)
        
        # Display results
        diff_tool.display_changes(changes)
        
        # Generate and save report if requested
        if output_file:
            report = diff_tool.generate_diff_report(changes, snapshot1_id, snapshot2_id)
            with open(output_file, 'w') as f:
                f.write(report)
            console.print(f"📄 Report saved to: {output_file}", style="green")
        
        return changes
        
    except Exception as e:
        console.print(f"Error comparing schemas: {e}", style="red")
        return []


if __name__ == "__main__":
    # Example usage
    import click
    
    @click.command()
    @click.argument('snapshot1', type=int)
    @click.argument('snapshot2', type=int)
    @click.option('--output', '-o', help='Output file for the diff report')
    def diff(snapshot1, snapshot2, output):
        """Compare two schema snapshots."""
        diff_schemas(snapshot1, snapshot2, output)
    
    diff() 