# Dockerfile
FROM apache/airflow:3.1.5

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential && apt-get clean

# Switch to airflow user
USER airflow

# Copy and install Python requirements
COPY requirements.txt .
COPY setup.py .

# Create directories
RUN mkdir -p /opt/airflow/{database,scripts,schemas,dags} && \
    touch /opt/airflow/database/__init__.py && \
    touch /opt/airflow/scripts/__init__.py && \
    touch /opt/airflow/schemas/__init__.py

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -e .

# Run other code if needed.