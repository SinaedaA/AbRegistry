from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator, BranchPythonOperator
from datetime import datetime
import traceback

def task_find_new_files(upload_dir = '/opt/airflow/data/lab_uploads/', **context):
    """
    Task to find new lab data CSV files in the upload directory.
    """
    from pathlib import Path
    UPLOAD_DIR = Path(upload_dir)
    new_files = list(UPLOAD_DIR.glob("*"))
    
    print(f"Found {len(new_files)} new data files: {[f.name for f in new_files]}")
    context['ti'].xcom_push(key='return_value', value=[str(f) for f in new_files])
    return [str(f) for f in new_files]

def task_validate_csv(archive_dir = '/opt/airflow/data/archive/', **context):
    """
    Task to find and validate new lab data CSV files.
    """
    from scripts.load_lab_data import validate_new_csv, archive_invalid_file
    from pathlib import Path

    TODAY = context['ds_nodash']

    new_files = context['ti'].xcom_pull(task_ids='find_new_files')
    if not new_files:
        print("No new files to validate.")

    # Validate each file
    valid_files = []

    for file_str in new_files:
        result = validate_new_csv(file_str)

        if result['is_valid']:
            valid_files.append(file_str) # valid_files is gonna go to XCom, so has to be str paths
            file_path = Path(file_str) # but to get the file_name, we need Path object
            print(f"File {file_path.name} is valid with {result['row_count']} rows. Tagged for ingestion.")
        else:
            archive_invalid_file(file_str, archive_dir, 'invalid', TODAY)
            file_path = Path(file_str)
            print(f"✗ Archived invalid: {file_path.name}  → Reason: {result['error_msg']}")

    # Push to XCom for downstream tasks
    context['ti'].xcom_push(key='valid_files', value=valid_files)
    # show that it worked?
    print(f"Validation complete. {len(valid_files)}/{len(new_files)} files are valid.")
    
    # Branch decision
    if valid_files:
        return 'ingest_valid_files'
    else:
        return 'notify_no_valid_files'

def task_ingest_valid_files(**context):
    """
    Task to ingest valid lab data files into the database.
    """
    from scripts.load_lab_data import ingest_lab_data
    from scripts.load_lab_data import archive_invalid_file
    files = context['ti'].xcom_pull(task_ids='validate_csv', key='valid_files')
    print(files)
    for file_str in files:
        try:
            ingest_lab_data(file_str)
            print(f"✓ Ingested: {file_str}")
        except Exception as e:
            print(f"Error ingesting {file_str}: {e}")
            archive_invalid_file(file_str, '/opt/airflow/data/archive/', 'flagged', datetime.now().strftime('%Y%m%d'))
            raise

def task_notify_no_valid_files():
    """
    Task to notify that no valid files were found for ingestion.
    """
    print("No valid lab data files found for ingestion today.")

def task_archive_valid_files(archive_dir = '/opt/airflow/data/archive', **context):
    """
    Task to archive invalid files to a specified directory.
    """
    from pathlib import Path
    import shutil

    TODAY = context['ds_nodash']

    archive_path = Path(archive_dir) / 'valid' / TODAY
    archive_path.mkdir(parents=True, exist_ok=True)
    print(f"Archiving valid files to: {archive_path}")
    
    valid_files = context['ti'].xcom_pull(task_ids='validate_csv', key='valid_files')
    
    for file_path in valid_files:
        source = Path(file_path)
        dest = archive_path / source.name
        shutil.move(str(source), str(dest))
        print(f"✓ Archived valid: {source.name}")

def task_antpack_annotate_load(**context):
    """
    Task to annotate sequences using Antpack.
    """
    from scripts.antpack_annotation import main as antpack_main

    files = context['ti'].xcom_pull(task_ids='validate_csv', key='valid_files')
    print(files)
    for file_str in files:
        try:
            antpack_main(file_str)
            print(f"Annotated sequences from {file_str} successfully, and loaded them to antpack_annotations table.")
        except Exception as e:
            print(f"Error annotating sequences from {file_str}: {e}")
            traceback.print_exc()
            raise

def task_protparam_annotate_load(**context):
    """
    Task to annotate sequences using ProtParam.
    """
    from scripts.prot_param import main as protparam_main

    files = context['ti'].xcom_pull(task_ids='validate_csv', key='valid_files')
    print(files)
    for file_str in files:
        try:
            protparam_main(file_str)
            print(f"Annotated sequences from {file_str} successfully, and loaded them to protein_properties table.")
        except Exception as e:
            print(f"Error annotating sequences from {file_str}: {e}")
            traceback.print_exc()
            raise

def task_analyze_liabilities_load(**context):
    """
    Task to analyze liabilities in sequences and load them into the database.
    """
    from scripts.liabilities import main as liabilities_main

    files = context['ti'].xcom_pull(task_ids='validate_csv', key='valid_files')
    print(files)
    for file_str in files:
        try:
            liabilities_main(file_str)
            print(f"Analyzed liabilities from {file_str} successfully, and loaded them to liabilities table.")
        except Exception as e:
            print(f"Error analyzing liabilities from {file_str}: {e}")
            traceback.print_exc()
            raise

with DAG(
    dag_id = 'load_lab_data',
    start_date = datetime(2024, 1, 1),
    schedule = ('@daily'),
    catchup = False,
    description = 'Validate and load new lab antibody sequence data into the database'
) as dag:

    find_new_files = PythonOperator(
        task_id='find_new_files',
        python_callable=task_find_new_files
    )

    validate_csv = BranchPythonOperator(
        task_id='validate_csv',
        python_callable=task_validate_csv
    )
    
    ingest = PythonOperator(
        task_id='ingest_valid_files',
        python_callable=task_ingest_valid_files
    )
    
    antpack_annotation_load = PythonOperator(
        task_id='antpack_annotation_load',
        python_callable=task_antpack_annotate_load,
    )

    protparam_annotation_load = PythonOperator(
        task_id='protparam_annotation_load',
        python_callable=task_protparam_annotate_load,
    )

    liabilities = PythonOperator(
        task_id='liabilities_analysis_load',
        python_callable=task_analyze_liabilities_load,
    )

    notify = PythonOperator(
        task_id='notify_no_valid_files',
        python_callable=task_notify_no_valid_files
    )

    archive = PythonOperator(
        task_id='archive_files',
        python_callable=task_archive_valid_files,
        op_kwargs={'archive_dir': '/opt/airflow/data/archive/'}
    )
    find_new_files >> validate_csv
    validate_csv >> ingest >> antpack_annotation_load >> protparam_annotation_load >> liabilities >> archive
    validate_csv >> notify