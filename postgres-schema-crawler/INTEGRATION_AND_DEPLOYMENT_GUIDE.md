# PostgreSQL Schema Crawler - Integration and Deployment Guide

This guide covers three essential topics for deploying and integrating my PostgreSQL Schema Crawler in production environments. It's designed to be beginner-friendly and provide clear, actionable steps.

## Table of Contents

1. [Production Database Connection Setup](#production-database-connection-setup)
2. [Web Application Integration](#web-application-integration)
3. [Apache Airflow Scheduling](#apache-airflow-scheduling)

---

## Production Database Connection Setup

### Overview
When moving from development to production, you need to secure your database connections and follow enterprise best practices.

### Current State
My tool currently uses a simple `config.yaml` file with plain text credentials:
```yaml
database:
  host: localhost
  port: 5432
  name: temp1
  user: postgres
  password: Kingkong@1
  schema: public
```

### Production Best Practices

#### 1. Environment Variables (Recommended)
**Why?** Keeps sensitive data out of code files and makes deployment flexible.

**How to implement:**
```bash
# Linux/Mac - Set environment variables
export DB_HOST=your-prod-host.com
export DB_PORT=5432
export DB_NAME=production_database
export DB_USER=schema_crawler_user
export DB_PASSWORD=your_secure_password
export DB_SCHEMA=public

# Windows - Set environment variables
set DB_HOST=your-prod-host.com
set DB_PORT=5432
set DB_NAME=production_database
set DB_USER=schema_crawler_user
set DB_PASSWORD=your_secure_password
set DB_SCHEMA=public
```

**Update my config.yaml:**
```yaml
database:
  host: ${DB_HOST}
  port: ${DB_PORT}
  name: ${DB_NAME}
  user: ${DB_USER}
  password: ${DB_PASSWORD}
  schema: ${DB_SCHEMA}
```

#### 2. Create Dedicated Database User
**Why?** Security principle of least privilege - only give necessary permissions.

**SQL Commands:**
```sql
-- Create dedicated user for schema crawler
CREATE USER schema_crawler_user WITH PASSWORD 'secure_random_password';

-- Grant only necessary permissions
GRANT CONNECT ON DATABASE production_database TO schema_crawler_user;
GRANT USAGE ON SCHEMA public TO schema_crawler_user;
GRANT SELECT ON information_schema.tables TO schema_crawler_user;
GRANT SELECT ON information_schema.columns TO schema_crawler_user;
GRANT SELECT ON information_schema.table_constraints TO schema_crawler_user;
GRANT SELECT ON information_schema.key_column_usage TO schema_crawler_user;

-- For user tracking (if needed)
GRANT SELECT ON ddl_audit_log TO schema_crawler_user;
```

#### 3. Enable SSL/TLS Encryption
**Why?** Encrypts data in transit between your application and database.

**Configuration:**
```yaml
database:
  host: your-prod-host.com
  port: 5432
  name: production_database
  user: schema_crawler_user
  password: ${DB_PASSWORD}
  schema: public
  
  # SSL Configuration
  ssl_mode: require  # or 'verify-full' for strict verification
  ssl_cert: /path/to/client.crt
  ssl_key: /path/to/client.key
  ssl_ca: /path/to/ca.crt
```

#### 4. Network Security
**Firewall Rules:**
```bash
# Allow only from specific IP addresses
sudo ufw allow from 192.168.1.100 to any port 5432
sudo ufw allow from 10.0.0.50 to any port 5432
```

#### 5. Connection Pooling
**Why?** Improves performance and handles multiple concurrent connections.

**Configuration:**
```yaml
database:
  # ... other settings ...
  
  # Production connection settings
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30
  pool_recycle: 3600
  connect_timeout: 10
```

#### 6. Secrets Management
**Option A: HashiCorp Vault**
```bash
# Install and configure Vault
vault kv get -field=password secret/postgres/schema_crawler
```

**Option B: AWS Secrets Manager**
```python
import boto3
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='prod/postgres/schema_crawler')
```

**Option C: Azure Key Vault**
```python
from azure.keyvault.secrets import SecretClient
client = SecretClient(vault_url="https://vault.vault.azure.net/", credential=credential)
secret = client.get_secret("postgres-password")
```

### Production Configuration Example
```yaml
# config.production.yaml
database:
  host: ${DB_HOST:-prod-postgres.company.com}
  port: ${DB_PORT:-5432}
  name: ${DB_NAME:-production_db}
  user: ${DB_USER:-schema_crawler}
  password: ${DB_PASSWORD}
  schema: ${DB_SCHEMA:-public}
  
crawler:
  # Run during maintenance windows
  allowed_hours: [2, 3, 4]  # 2-4 AM only
  max_execution_time: 300   # 5 minutes max
  enable_notifications: true
  
output:
  data_dir: /var/lib/schema-crawler
  backup_retention_days: 90
  
logging:
  level: INFO
  file: /var/log/schema-crawler/app.log
  max_size_mb: 100
  backup_count: 5

alerts:
  email:
    smtp_server: mail.company.com
    recipients: ["dba@company.com", "devops@company.com"]
  webhook:
    url: https://hooks.slack.com/services/your/webhook/url
```

### Production Checklist
- ✅ Use environment variables for credentials
- ✅ Create dedicated database user with minimal permissions
- ✅ Enable SSL/TLS encryption
- ✅ Configure firewall rules
- ✅ Set up connection pooling
- ✅ Implement health checks
- ✅ Configure logging and monitoring
- ✅ Set up automated backups
- ✅ Test connection failover
- ✅ Document access procedures
- ✅ Regular security audits

---

## Web Application Integration

### Overview
My current PostgreSQL Schema Crawler is built as a **Streamlit application** (frontend interface), not a backend API service. To integrate with your existing web application, you need to understand the current architecture and choose the best integration approach.

### Current Architecture
```
Streamlit App (enhanced_web_ui.py)
    ↓
Direct Database Calls (SQLite + PostgreSQL)
    ↓
No API Endpoints (Everything is frontend-based)
```

### Database Connections in My Current App

**1. PostgreSQL Connection (for schema crawling):**
- **Location**: `src/schema_crawler.py` → `DatabaseConnection` class
- **Usage**: Direct database connection for reading schema metadata
- **Configuration**: `config.yaml` file

**2. SQLite Connection (for metadata storage):**
- **Location**: Multiple files - `src/web_ui.py`, `enhanced_web_ui.py`
- **Usage**: Direct file-based SQLite operations
- **Storage**: `data/schema_metadata.db`

### Integration Options

#### Option 1: API-fy Your Schema Crawler (Recommended)

Convert my tool into a REST API service that your existing web app can consume.

**Step 1: Create Flask/FastAPI Backend**
```python
# api_server.py (new file you'd create)
from flask import Flask, jsonify, request
from src.schema_crawler import DatabaseConnection, SchemaCrawler
from src.schema_diff import SchemaDiff
import sqlite3
import json

app = Flask(__name__)

# API Endpoints you'd add:

@app.route('/api/snapshots', methods=['GET'])
def get_snapshots():
    """Get all schema snapshots"""
    conn = sqlite3.connect("data/schema_metadata.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, schema_name FROM schema_snapshots ORDER BY timestamp DESC")
    snapshots = cursor.fetchall()
    conn.close()
    return jsonify([{"id": s[0], "timestamp": s[1], "schema": s[2]} for s in snapshots])

@app.route('/api/snapshots/<int:snapshot_id>', methods=['GET'])
def get_snapshot(snapshot_id):
    """Get specific snapshot details"""
    diff_engine = SchemaDiff()
    snapshot = diff_engine.get_snapshot(snapshot_id)
    return jsonify(snapshot)

@app.route('/api/snapshots', methods=['POST'])
def create_snapshot():
    """Take new schema snapshot"""
    # Your crawling logic here
    pass

@app.route('/api/compare/<int:id1>/<int:id2>', methods=['GET'])
def compare_snapshots(id1, id2):
    """Compare two snapshots"""
    diff_engine = SchemaDiff()
    snapshot1 = diff_engine.get_snapshot(id1)
    snapshot2 = diff_engine.get_snapshot(id2)
    changes = diff_engine.compare_schemas(snapshot1, snapshot2)
    return jsonify([{"type": c.change_type, "object": c.object_type, "name": c.object_name, "details": c.details} for c in changes])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

**Step 2: Your Web App Integration**
```javascript
// In your existing web application
async function getSchemaSnapshots() {
    const response = await fetch('http://localhost:5000/api/snapshots');
    return await response.json();
}

async function compareSchemas(id1, id2) {
    const response = await fetch(`http://localhost:5000/api/compare/${id1}/${id2}`);
    return await response.json();
}

async function takeSnapshot() {
    const response = await fetch('http://localhost:5000/api/snapshots', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    return await response.json();
}
```

#### Option 2: Embed Streamlit in Your Web App

**Using iframe:**
```html
<!-- In your existing web application -->
<iframe 
    src="http://localhost:8501" 
    width="100%" 
    height="800px"
    frameborder="0">
</iframe>
```

**Using Streamlit components:**
```python
# In your Streamlit app, add this for embedding
import streamlit.components.v1 as components

# Allow embedding
st.set_page_config(
    page_title="Schema Crawler",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Add custom CSS for embedding
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)
```

#### Option 3: Direct Database Access (Not Recommended)

Your existing web app could directly access my SQLite database:

```python
# In your existing web application backend
import sqlite3

def get_schema_snapshots():
    conn = sqlite3.connect("path/to/schema_metadata.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, schema_name FROM schema_snapshots ORDER BY timestamp DESC")
    snapshots = cursor.fetchall()
    conn.close()
    return snapshots
```

**⚠️ Issues with this approach:**
- File locking conflicts
- No business logic layer
- Direct database coupling

#### Option 4: Microservice Architecture (Enterprise)

Deploy as separate microservice:

```yaml
# docker-compose.yml
version: '3.8'
services:
  schema-crawler-api:
    build: ./schema-crawler
    ports:
      - "5000:5000"
    environment:
      - DB_HOST=your-postgres-host
      - DB_PASSWORD=your-password
    volumes:
      - ./data:/app/data

  your-web-app:
    build: ./your-app
    ports:
      - "3000:3000"
    environment:
      - SCHEMA_CRAWLER_API=http://schema-crawler-api:5000
```

### Recommended Integration Approach

#### For Most Use Cases: REST API Conversion

**1. Create API Layer:**
```python
# schema_api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Schema Crawler API", version="1.0.0")

# Enable CORS for your web app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your web app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your API endpoints here...

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**2. Update Your Web App:**
```javascript
// api.js in your web application
const SCHEMA_API_BASE = 'http://localhost:8000';

export const schemaAPI = {
    async getSnapshots() {
        const response = await fetch(`${SCHEMA_API_BASE}/api/snapshots`);
        if (!response.ok) throw new Error('Failed to fetch snapshots');
        return response.json();
    },
    
    async takeSnapshot() {
        const response = await fetch(`${SCHEMA_API_BASE}/api/snapshots`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('Failed to create snapshot');
        return response.json();
    },
    
    async compareSnapshots(id1, id2) {
        const response = await fetch(`${SCHEMA_API_BASE}/api/compare/${id1}/${id2}`);
        if (!response.ok) throw new Error('Failed to compare snapshots');
        return response.json();
    }
};
```

**3. Use in Your Frontend:**
```jsx
// In your React/Vue/Angular component
import { schemaAPI } from './api';

function SchemaMonitor() {
    const [snapshots, setSnapshots] = useState([]);
    
    useEffect(() => {
        schemaAPI.getSnapshots()
            .then(setSnapshots)
            .catch(console.error);
    }, []);
    
    const handleTakeSnapshot = async () => {
        try {
            await schemaAPI.takeSnapshot();
            // Refresh snapshots
            const updated = await schemaAPI.getSnapshots();
            setSnapshots(updated);
        } catch (error) {
            console.error('Error taking snapshot:', error);
        }
    };
    
    return (
        <div>
            <button onClick={handleTakeSnapshot}>Take Snapshot</button>
            <ul>
                {snapshots.map(s => (
                    <li key={s.id}>{s.timestamp} - {s.schema}</li>
                ))}
            </ul>
        </div>
    );
}
```

### Summary
**Current State:** No API endpoints - everything is Streamlit frontend with direct database calls

**Best Integration Option:** Convert to REST API service that your existing web app can consume

**Quick Start:** Create a Flask/FastAPI wrapper around my existing `SchemaCrawler` and `SchemaDiff` classes

---

## Apache Airflow Scheduling

### Overview
Apache Airflow is an enterprise-grade workflow management platform that's much more powerful than Windows Task Scheduler. It's perfect for production environments where you need reliability, monitoring, and complex scheduling.

### Why Use Airflow Instead of Windows Task Scheduler?

**Advantages:**
- ✅ **Centralized Management**: All workflows in one place
- ✅ **Monitoring & Alerting**: Built-in success/failure tracking
- ✅ **Retry Logic**: Automatic retries with exponential backoff
- ✅ **Dependencies**: Complex task dependencies and workflows
- ✅ **Scalability**: Can handle multiple environments and teams
- ✅ **Version Control**: Workflows can be version controlled
- ✅ **Web UI**: Rich interface for monitoring and debugging
- ✅ **Logging**: Comprehensive logging and audit trails
- ✅ **Cross-Platform**: Works on any OS, not just Windows

### Airflow DAG Structure

You'd create a DAG (Directed Acyclic Graph) with multiple tasks for my tool:

```python
# schema_crawler_dag.py
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta
import os

default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'postgres_schema_crawler',
    default_args=default_args,
    description='PostgreSQL Schema Crawler DAG',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    catchup=False
)
```

### Task Definitions

**Task 1: Schema Snapshot**
```python
def take_schema_snapshot(**context):
    """Take a new schema snapshot"""
    import subprocess
    import sys
    
    # Set environment variables for database connection
    os.environ['DB_HOST'] = 'your-prod-host'
    os.environ['DB_PASSWORD'] = context['dag_run'].conf.get('db_password', 'default')
    
    # Run the schema crawler
    result = subprocess.run([
        sys.executable, 'src/schema_crawler.py', 'crawl'
    ], capture_output=True, text=True, cwd='/path/to/schema-crawler')
    
    if result.returncode != 0:
        raise Exception(f"Schema crawl failed: {result.stderr}")
    
    return "Schema snapshot completed successfully"

snapshot_task = PythonOperator(
    task_id='take_schema_snapshot',
    python_callable=take_schema_snapshot,
    dag=dag
)
```

**Task 2: Generate Change Report**
```python
def generate_change_report(**context):
    """Generate change report comparing with previous snapshot"""
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, 'src/schema_crawler.py', 'diff-latest',
        '--output', f'reports/changes_{datetime.now().strftime("%Y%m%d")}.md'
    ], capture_output=True, text=True, cwd='/path/to/schema-crawler')
    
    if result.returncode != 0:
        raise Exception(f"Change report generation failed: {result.stderr}")
    
    return "Change report generated successfully"

report_task = PythonOperator(
    task_id='generate_change_report',
    python_callable=generate_change_report,
    dag=dag
)
```

**Task 3: Send Notifications**
```python
def send_notification(**context):
    """Send notification if changes detected"""
    import subprocess
    import sys
    
    # Check if changes were detected
    result = subprocess.run([
        sys.executable, 'src/schema_crawler.py', 'diff-latest'
    ], capture_output=True, text=True, cwd='/path/to/schema-crawler')
    
    if "No changes detected" not in result.stdout:
        # Send Slack/email notification
        send_slack_notification("Schema changes detected! Check the report.")
    
    return "Notification sent"

notification_task = PythonOperator(
    task_id='send_notification',
    python_callable=send_notification,
    dag=dag
)
```

### Task Dependencies

```python
# Define task dependencies
snapshot_task >> report_task >> notification_task
```

### Advanced DAG with Multiple Schedules

```python
# Weekly comparison DAG
weekly_dag = DAG(
    'postgres_schema_weekly_report',
    default_args=default_args,
    description='Weekly Schema Comparison Report',
    schedule_interval='0 3 * * 0',  # Sundays at 3 AM
    catchup=False
)

# Monthly cleanup DAG
monthly_dag = DAG(
    'postgres_schema_cleanup',
    default_args=default_args,
    description='Monthly Schema Cleanup',
    schedule_interval='0 4 1 * *',  # 1st of month at 4 AM
    catchup=False
)
```

### Environment Configuration

**Airflow Variables:**
```bash
# Set in Airflow UI or via CLI
airflow variables set DB_HOST "your-prod-postgres-host"
airflow variables set DB_NAME "production_database"
airflow variables set DB_USER "schema_crawler_user"
airflow variables set SCHEMA_CRAWLER_PATH "/opt/schema-crawler"
```

**Airflow Connections:**
```bash
# Database connection for Airflow
airflow connections add 'postgres_schema_crawler' \
    --conn-type 'postgres' \
    --conn-host 'your-prod-host' \
    --conn-login 'schema_crawler_user' \
    --conn-password 'your-password' \
    --conn-schema 'public'
```

### Docker Integration

**Dockerfile for Airflow:**
```dockerfile
FROM apache/airflow:2.7.1

# Install your schema crawler dependencies
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

# Copy your schema crawler code
COPY . /opt/schema-crawler/
WORKDIR /opt/schema-crawler

# Set environment variables
ENV PYTHONPATH=/opt/schema-crawler
```

**Docker Compose:**
```yaml
version: '3.8'
services:
  airflow-webserver:
    build: .
    ports:
      - "8080:8080"
    environment:
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
      - ./schema-crawler:/opt/schema-crawler
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:13
    environment:
      - POSTGRES_USER=airflow
      - POSTGRES_PASSWORD=airflow
      - POSTGRES_DB=airflow
    volumes:
      - postgres-db-volume:/var/lib/postgresql/data
```

### Monitoring and Alerting

**Task Success/Failure Handling:**
```python
def on_failure_callback(context):
    """Handle task failures"""
    task_instance = context['task_instance']
    dag_id = context['dag'].dag_id
    task_id = context['task'].task_id
    
    # Send alert
    send_slack_notification(
        f"❌ Airflow task failed: {dag_id}.{task_id}\n"
        f"Error: {context['exception']}"
    )

# Add to DAG
dag = DAG(
    'postgres_schema_crawler',
    default_args=default_args,
    on_failure_callback=on_failure_callback,
    # ... other args
)
```

**Custom Sensors:**
```python
from airflow.sensors.base import BaseSensorOperator

class DatabaseHealthSensor(BaseSensorOperator):
    """Sensor to check database connectivity before running tasks"""
    
    def poke(self, context):
        try:
            # Test database connection
            db = DatabaseConnection(...)
            return db.connect()
        except Exception:
            return False

# Use in DAG
health_check = DatabaseHealthSensor(
    task_id='check_database_health',
    poke_interval=60,  # Check every minute
    timeout=300,       # Timeout after 5 minutes
    dag=dag
)

health_check >> snapshot_task
```

### Advanced Scheduling Patterns

**Conditional Execution:**
```python
def should_run_snapshot(**context):
    """Check if snapshot should run based on business rules"""
    # Check if it's a business day
    # Check if database is in maintenance mode
    # Check if previous snapshot was successful
    return True

conditional_task = BranchPythonOperator(
    task_id='check_conditions',
    python_callable=should_run_snapshot,
    dag=dag
)
```

**Parallel Processing:**
```python
# Multiple schema crawling in parallel
schemas = ['public', 'analytics', 'staging']

for schema in schemas:
    task = PythonOperator(
        task_id=f'crawl_schema_{schema}',
        python_callable=take_schema_snapshot,
        op_kwargs={'schema': schema},
        dag=dag
    )
    # Add to parallel group
```

### Migration Path

**Phase 1: Basic Migration**
- Move existing Windows tasks to Airflow DAGs
- Keep same schedule and logic
- Add basic error handling

**Phase 2: Enhancement**
- Add monitoring and alerting
- Implement retry logic
- Add health checks

**Phase 3: Advanced Features**
- Conditional execution
- Parallel processing
- Integration with other data pipelines

### Use Cases for Airflow
- **Enterprise Environments**: Multiple teams, complex dependencies
- **Data Pipelines**: Integration with other ETL processes
- **Multi-Environment**: Dev, staging, production workflows
- **Compliance**: Audit trails and governance requirements

---

## Summary

This guide covers three critical aspects of production deployment for my tool:

1. **Production Database Connections**: Secure, scalable database access with proper authentication and encryption
2. **Web Application Integration**: Converting my Streamlit app into a reusable API service
3. **Apache Airflow Scheduling**: Enterprise-grade workflow management for reliable, monitored automation

Each section provides beginner-friendly explanations with practical examples and step-by-step instructions. Choose the approach that best fits your organization's needs and technical requirements.

### Quick Reference

| Topic | Current State | Production Approach | Benefits |
|-------|---------------|-------------------|----------|
| **Database Connections** | Plain text in config.yaml | Environment variables + SSL | Security, flexibility |
| **Web Integration** | Streamlit frontend only | REST API service | Reusability, scalability |
| **Scheduling** | Windows Task Scheduler | Apache Airflow | Reliability, monitoring |

This approach ensures my PostgreSQL Schema Crawler is production-ready with proper security, reliability, and integration capabilities. 