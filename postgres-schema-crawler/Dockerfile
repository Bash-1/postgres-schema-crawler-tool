FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional scheduling dependencies
RUN pip install --no-cache-dir schedule

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs reports

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port for web interface
EXPOSE 8501

# Default command
CMD ["python", "scheduled_crawler.py"] 