from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
from scripts.db_setup import init_db, create_tables
from scripts.load_sabdab import load_sabdab_data
from scripts.antpack_annotation import main as antpack
from scripts.prot_param import main as prot_param

def task_validate_sabdab_csv(**context):
    """
    Task to validate the SAbDab CSV file before loading.
    """
    from scripts.load_sabdab import validate_sabdab_csv

    result = validate_sabdab_csv()
    
    if not result['is_valid']:
        raise ValueError(f"SAbDab CSV validation failed: {result['error_msg']}")
    
    print(f"✓ Valid SAbDab CSV file: {result['row_count']} rows. Proceeding to load.")

with DAG(
    dag_id = 'setup_database',
    start_date = datetime(2024, 1, 1),
    schedule = None,
    catchup = False,
    description = 'Initialize database schemas, create tables, and load SAdDab data'
) as dag:
    
    reset_potential_names = BashOperator(
        task_id='reset_potential_names',
        bash_command="cp /opt/airflow/data/raw/potential_names_master.json /opt/airflow/data/raw/potential_names.json"
    )

    init_db_task = PythonOperator(
        task_id='init_db',
        python_callable=init_db
    )

    create_tables_task = PythonOperator(
        task_id='create_tables',
        python_callable=create_tables
    )

    validate_sabdab_task = PythonOperator(
        task_id='validate_sabdab_csv',
        python_callable=task_validate_sabdab_csv
    )

    load_data_task = PythonOperator(
        task_id='load_sabdab_data',
        python_callable=load_sabdab_data
    )

    annotate_sabdab_task = PythonOperator(
        task_id='annotate_sabdab',
        python_callable=antpack
    )

    prot_param_task = PythonOperator(
        task_id='compute_protein_properties',
        python_callable=prot_param
    )

    reset_potential_names >> init_db_task >> create_tables_task >> validate_sabdab_task >> load_data_task >> annotate_sabdab_task >> prot_param_task