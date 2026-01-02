from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime
from scripts.init_db import main as init_db
from scripts.create_tables import main as create_tables
from scripts.load_data import main as load_data

with DAG(
    dag_id = 'setup_database',
    start_date = datetime(2024, 1, 1),
    schedule = None,
    catchup = False,
    description = 'Initialize database schemas, create tables, and load SAdDab data'
) as dag:
    
    init_db_task = PythonOperator(
        task_id='init_db',
        python_callable=init_db
    )

    create_tables_task = PythonOperator(
        task_id='create_tables',
        python_callable=create_tables
    )

    load_data_task = PythonOperator(
        task_id='load_data',
        python_callable=load_data
    )

    init_db_task >> create_tables_task >> load_data_task