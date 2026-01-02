import polars as pl
from database.database import SessionLocal, engine
from database.models import RawSequence
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
        'missing_columns': []
    }
    
    try:
        df = pl.read_csv(file_path)
    except Exception as e:
        result['error_type'] = 'corrupted_or_invalid_format'
        result['error_msg'] = f"Cannot read file: {str(e)}"
        return result
    if df.is_empty():
        result['error_type'] = 'empty_file'
        result['error_msg'] = "The file is empty."
        return result
    required_columns = {'ab_name', 'ab_format', 'vd_lc', 'heavy_chain1', 'researcher'}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        result['error_type'] = 'missing_columns'
        result['missing_columns'] = list(missing_columns)
        result['error_msg'] = f"Missing required columns: {', '.join(missing_columns)}"
        return result
    result['is_valid'] = True
    result['row_count'] = df.height
    return result

def ingest_lab_data(file_path: str):
    """Ingest validated lab data CSV into the database."""
    df = pl.read_csv(file_path)
    session = SessionLocal()
    try:
        for i, row in enumerate(df.iter_rows(named=True)):
            record = RawSequence(
                source='Lab Upload',
                imported_at=datetime.utcnow(),
                ab_name=row['ab_name'],
                ab_format=row.get('ab_format'),
                ch1_isotype=row.get('ch1_isotype'),
                vd_lc=row.get('vd_lc'),
                heavy_chain1=row['heavy_chain1'],
                light_chain1=row.get('light_chain1') or None,
                heavy_chain2=row.get('heavy_chain2') or None,
                light_chain2=row.get('light_chain2') or None,
                target=row.get('target') or None,
                notes=row.get('notes') or None,
                genetics=row.get('genetics') or None,
                development_metadata={
                    'lab_name': row.get('lab_name'),
                    'researcher': row.get('reseacher'),
                    'project_id': row.get('project_id') or None,
                    'project': row.get('project')
                },
                structural_metadata={}
            )
            session.add(record)
        session.commit()
        print(f"Ingested {df.height} records from {file_path} into the database.")
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