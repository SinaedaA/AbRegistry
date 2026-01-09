import polars as pl
from database.database import SessionLocal, engine
from database.models import RawSequence
from schemas.validation import LabSequenceInput
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from datetime import datetime
import traceback

def validate_new_csv(file_path: str) -> dict:
    """Returns validation result with details"""
    result = {
        'is_valid': False,
        'file_path': file_path,
        'error_type': None,  # 'format', 'columns', 'empty', 'corrupted'
        'error_msg': None,
        'row_count': 0,
        'missing_columns': [],
        'invalid_rows': []
    }
    
    # 1. Check that the CSV is readable by polars
    try:
        df = pl.read_csv(file_path)
    except Exception as e:
        result['error_type'] = 'corrupted_or_invalid_format'
        result['error_msg'] = f"Cannot read file: {str(e)}"
        return result
    
    # 2. Return "empty file" error if no rows
    if df.is_empty():
        result['error_type'] = 'empty_file'
        result['error_msg'] = "The file is empty."
        return result
    
    # 3. Check that required columns are present in the DataFrame 
    required_columns = {'ab_name', 'ab_format', 'vd_lc', 'target', 'development_tech', 'heavy_chain1', 'researcher', 'conditions_active'}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        result['error_type'] = 'missing_columns'
        result['missing_columns'] = list(missing_columns)
        result['error_msg'] = f"Missing required columns: {', '.join(missing_columns)}"
        return result
    
    # 4. Validate each row using the pydantic validation schema
    for i, row in enumerate(df.iter_rows(named=True)):
        try:
            LabSequenceInput(**row)
        except ValidationError as e:
            result['invalid_rows'].append({
                'row_number': i + 1,
                'ab_name': row.get('ab_name', '<missing>'),
                'errors': [err['msg'] for err in e.errors()]
            })
    
    # 5. If there are invalid rows, return details of the errors
    if result['invalid_rows']:
        result['error_type'] = 'invalid_rows'
        result['error_msg'] = f"Found {len(result['invalid_rows'])} invalid rows."
        return result
    
    # 6. If all checks pass, return valid result
    result['is_valid'] = True
    result['row_count'] = df.height
    return result

def ingest_lab_data(file_path: str):
    """Ingest validated lab data CSV into the database."""
    df = pl.read_csv(file_path)
    session = SessionLocal()

    ####### DEV ONLY #######
    inserted = 0
    skipped = 0
    ####### END DEV ONLY #######

    try:
        for i, row in enumerate(df.iter_rows(named=True)):
            print(f"Ingesting row {i+1}/{df.height}: {row['ab_name']}")
            record = RawSequence(
                source='Lab Upload',
                imported_at=datetime.utcnow(),
                ab_name=row['ab_name'],
                ab_format=row.get('ab_format'),
                ch1_isotype=row.get('ch1_isotype') or None,
                vd_lc=row.get('vd_lc'),
                heavy_chain1=row['heavy_chain1'],
                light_chain1=row.get('light_chain1') or None,
                heavy_chain2=row.get('heavy_chain2') or None,
                light_chain2=row.get('light_chain2') or None,
                target=row.get('target'),
                notes=row.get('notes') or None,
                genetics=row.get('genetics'),
                development_metadata={
                    'company': row.get('company'),
                    'researcher': row.get('researcher'),
                    'project_id': row.get('project_id') or None,
                    'project': row.get('project'),
                    'conditions_active': row.get('conditions_active'),
                },
                structural_metadata={}
            )
            ####### DEV ONLY #######
            try:
                session.add(record)
                session.flush()
                inserted += 1
            except IntegrityError as ie:
                session.rollback()
                print(f"⚠️  Skipping duplicate entry for ab_name: {row['ab_name']}")
                skipped += 1
            ####### END DEV ONLY #######
        
        session.commit()
        print(f"✓ Ingestion complete. {inserted} records inserted, {skipped} records skipped due to duplicates.")
        #print(f"Ingested {df.height} records from {file_path} into the database.")
    except Exception as e:
        session.rollback()
        print(f"Error ingesting data from {file_path}: {e}")
        traceback.print_exc()
        raise
    finally:
        session.close()
    return

def archive_invalid_file(file_path: str, archive_dir: str, dir_flag: str, date: str):
    from pathlib import Path
    import shutil
    source = Path(file_path)
    archive_path = Path(archive_dir) / dir_flag / date
    archive_path.mkdir(parents=True, exist_ok=True)
    dest = archive_path / source.name
    shutil.move(str(source), str(dest))