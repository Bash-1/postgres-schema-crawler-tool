# PostgreSQL Schema Crawler

I built this lightweight tool that crawls PostgreSQL database schemas, tracks changes over time, and provides both CLI and web interfaces for schema management and comparison.

## Features

- **Schema Discovery**: Automatically discover and catalog all tables, columns, and constraints
- **Change Detection**: Compare schema snapshots to detect additions, removals, and modifications
- **Version History**: Maintain a complete history of schema changes with timestamps
- **Multiple Output Formats**: Export schemas as JSON, CSV, or Markdown
- **Rich CLI Interface**: Beautiful terminal output with tables and progress indicators
- **Web Dashboard**: Interactive Streamlit web interface for schema exploration
- **Metadata Storage**: Store custom descriptions, ownership, and tags
- **Scheduled Crawling**: Support for automated schema monitoring

## Requirements

To use my tool, you'll need:
- Python 3.8+
- PostgreSQL database access
- Required Python packages (see `requirements.txt`)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd postgres-schema-crawler
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure database connection**:
   Edit `config.yaml` with your PostgreSQL credentials:
   ```yaml
   database:
     host: localhost
     port: 5432
     name: your_database
     user: your_username
     password: your_password
     schema: public
   ```

## Usage

### CLI Interface

My tool provides a comprehensive command-line interface with multiple commands:

#### 1. Crawl Schema
```bash
# Basic crawl with default settings
python src/schema_crawler.py crawl

# Custom database connection
python src/schema_crawler.py crawl --host localhost --port 5432 --database mydb --user postgres --password mypass --schema public

# Table filtering examples
python src/schema_crawler.py crawl --include-tables employees departments
python src/schema_crawler.py crawl --exclude-tables temp_table backup_table
python src/schema_crawler.py crawl --include-patterns "user*" "*_log"
python src/schema_crawler.py crawl --exclude-patterns "*_backup" "test_*"
python src/schema_crawler.py crawl --include-tables employees --include-patterns "dept*" --exclude-patterns "*_temp"
```

#### 2. List Snapshots
```bash
# View all saved schema snapshots
python src/schema_crawler.py list-snapshots
```

#### 3. Compare Schemas
```bash
# Compare two specific snapshots
python src/schema_crawler.py diff 1 2

# Compare the two most recent snapshots
python src/schema_crawler.py diff-latest

# Generate a diff report
python src/schema_crawler.py diff 1 2 --output changes.md
```

#### 4. Export Schemas
```bash
# Export as JSON
python src/schema_crawler.py export 1 --format json

# Export as CSV
python src/schema_crawler.py export 1 --format csv

# Export as Markdown
python src/schema_crawler.py export 1 --format markdown
```

### Web Interface

Launch my interactive web dashboard:

```bash
streamlit run src/web_ui.py
```

My web interface provides:
- **Dashboard**: Overview of schema snapshots and activity
- **Schema Crawler**: Interactive database connection and crawling
- **Schema History**: Browse and export historical snapshots
- **Schema Comparison**: Visual comparison of schema changes
- **Settings**: Configure database connections and preferences

## Schema Information Captured

My tool captures comprehensive metadata for each schema object:

### Tables
- Table name and type (BASE TABLE, VIEW, FOREIGN TABLE)
- Table owner
- Creation timestamp
- Custom descriptions and tags

### Columns
- Column name and data type
- Nullability constraints
- Default values
- Ordinal position
- Character length, numeric precision, scale
- Custom descriptions

### Constraints
- Primary keys
- Foreign keys
- Unique constraints
- Check constraints
- Not null constraints

## Change Detection

My schema diffing engine detects:

- **Added Objects**: New tables, columns, or constraints
- **Removed Objects**: Deleted tables, columns, or constraints
- **Modified Objects**: Changes to data types, nullability, defaults, etc.

### Example Diff Output
```
Schema Changes Summary:
  Added: 2 | Removed: 1 | Modified: 3

🟢 Added Objects (2):
┌────────┬──────────────┬────────┬─────────────────────────────────────┐
│ Type   │ Name         │ Parent │ Details                             │
├────────┼──────────────┼────────┼─────────────────────────────────────┤
│ Table  │ new_table    │ -      │ Table 'new_table' was added         │
│ Column │ status       │ users  │ Column 'status' was added to table  │
└────────┴──────────────┴────────┴─────────────────────────────────────┘
```

## Project Structure

```
postgres-schema-crawler/
├── src/
│   ├── schema_crawler.py    # Main crawler and CLI interface
│   ├── schema_diff.py       # Schema comparison engine
│   └── web_ui.py           # Streamlit web interface
├── data/
│   ├── schema_metadata.db   # SQLite database for snapshots
│   └── annotations.yaml     # Custom metadata annotations
├── config.yaml             # Configuration file
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Configuration

### Database Settings
Configure your PostgreSQL connection in my `config.yaml`:

```yaml
database:
  host: localhost
  port: 5432
  name: your_database
  user: your_username
  password: your_password
  schema: public
```

### Crawler Settings
```yaml
crawler:
  include_types:
    - BASE TABLE
    - VIEW
    - FOREIGN TABLE
  max_tables: 0  # 0 = unlimited
  include_constraints: true
  include_indexes: false
```

### Table Filtering
My tool supports powerful table filtering to focus on specific tables:

```yaml
crawler:
  table_filter:
    # Include only specific tables
    include_tables: 
      - employees
      - departments
      - salaries
    
    # Exclude specific tables
    exclude_tables:
      - temp_table
      - backup_table
    
    # Include tables matching patterns (supports wildcards)
    include_patterns:
      - "user*"        # Tables starting with "user"
      - "*_log"        # Tables ending with "_log"
      - "temp_*"       # Tables starting with "temp_"
    
    # Exclude tables matching patterns
    exclude_patterns:
      - "*_backup"     # Exclude backup tables
      - "test_*"       # Exclude test tables
      - "*_old"        # Exclude old tables
    
    # Case sensitive pattern matching
    case_sensitive: false
```

**My Filtering Options:**
- `include_tables`: List of specific tables to include (empty = all tables)
- `exclude_tables`: List of specific tables to exclude
- `include_patterns`: Wildcard patterns for tables to include
- `exclude_patterns`: Wildcard patterns for tables to exclude
- `case_sensitive`: Whether pattern matching is case sensitive

**My Pattern Examples:**
- `"user*"` - Tables starting with "user"
- `"*_log"` - Tables ending with "_log"
- `"temp_*"` - Tables starting with "temp_"
- `"*_backup"` - Tables ending with "_backup"

### Output Settings
```yaml
output:
  data_dir: data
  export_format: json
  create_reports: true
```

## Use Cases

### 1. Database Documentation
- Generate comprehensive schema documentation
- Track schema evolution over time
- Maintain up-to-date data dictionaries

### 2. Change Management
- Monitor schema changes in development environments
- Validate migration scripts
- Ensure compliance with schema standards

### 3. Data Governance
- Track ownership and responsibility
- Monitor data lineage
- Maintain audit trails

### 4. Development Workflow
- Compare development and production schemas
- Validate database migrations
- Document schema changes for releases

## Automation

### Scheduled Crawling
Set up automated schema monitoring using cron:

```bash
# Crawl schema daily at 2 AM
0 2 * * * cd /path/to/postgres-schema-crawler && python src/schema_crawler.py crawl

# Compare with previous day
0 3 * * * cd /path/to/postgres-schema-crawler && python src/schema_crawler.py diff-latest --output daily_changes.md
```

### CI/CD Integration
Integrate my schema validation into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Validate Schema Changes
  run: |
    python src/schema_crawler.py crawl
    python src/schema_crawler.py diff-latest --output schema_changes.md
    # Fail if breaking changes detected
    if grep -q "removed\|modified" schema_changes.md; then
      echo "Breaking schema changes detected!"
      exit 1
    fi
```

## Security Considerations

- Store database credentials securely (use environment variables)
- Limit database user permissions to read-only access
- Regularly rotate database passwords
- Use SSL connections for production databases

## 🤝 Contributing

I welcome contributions! Here's how you can help:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you need help with my tool:
1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information

## 🗺️ Roadmap

- [ ] Support for other database systems (MySQL, SQL Server)
- [ ] Advanced visualization and reporting
- [ ] Integration with dbt and other data tools
- [ ] API endpoints for programmatic access
- [ ] Advanced change impact analysis
- [ ] Schema validation rules engine 