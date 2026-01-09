import polars as pl
from database.database import SessionLocal, engine
from sqlalchemy.exc import IntegrityError
from database.models import RawSequence
from datetime import datetime
import traceback

SABDAB_DB_PATH = 'data/raw/sabdab_summary.csv'

def validate_sabdab_csv(file_path = SABDAB_DB_PATH) -> dict:
    """Light validation - just check file integrity"""
    result = {'is_valid': False, 'error_msg': None}
    
    try:
        df = pl.read_csv(file_path)
    except Exception as e:
        result['error_msg'] = f"Cannot read file: {e}"
        return result
    
    if df.is_empty():
        result['error_msg'] = "File is empty"
        return result
    
    # Check expected columns exist
    expected = {'Therapeutic', 'HeavySequence', 'LightSequence'}
    if not expected.issubset(set(df.columns)):
        result['error_msg'] = f"Missing expected columns"
        return result
    
    result['is_valid'] = True
    result['row_count'] = len(df)
    return result

def load_sabdab_data():
    print("Loading initial data into 'staging.raw_sequences' table...")
    db = SessionLocal()
    # Load data from a CSV file using Polars
    df = pl.read_csv(SABDAB_DB_PATH)
    # replace column names with those matching RawSequence model
    df = df.rename({
        'Therapeutic': 'ab_name',
        'Format': 'ab_format',
        'CH1 Isotype': 'ch1_isotype',
        'VD LC': 'vd_lc',
        "Highest_Clin_Trial (Feb '25)": 'highest_clinical_phase',
        'Est. Status': 'dev_status',
        'HeavySequence': 'heavy_chain1',
        'LightSequence': 'light_chain1',
        'HeavySequence(ifbispec)': 'heavy_chain2',
        'LightSequence(ifbispec)': 'light_chain2',
        '100% SI Structure': 'si_struct_100',
        '99% SI Structure': 'si_struct_99',
        '95-98% SI Structure': 'si_struct_95_98',
        'Year Proposed': 'year_proposed',
        'Year Recommended': 'year_recommended',
        'Target': 'target',
        'Companies': 'companies',
        'Conditions Approved': 'conditions_approved',
        'Conditions Active': 'conditions_active',
        'Conditions Discontinued': 'conditions_discontinued',
        'Development Tech': 'dev_tech',
        'Notes': 'notes',
        'Genetics (Bispecifics delimited with semicolon)': 'genetics',
        'Alternative Therapeutic Names': 'alt_therapeutic_uses'
    })
    # Write it to CSV for other scripts
    df.write_csv('data/processed/sabdab_renamed.csv')
    # Convert Polars DataFrame to list of RawSequence objects
    thera_records = []

    ####### DEV ONLY #######
    inserted = 0
    skipped = 0
    ####### END DEV ONLY #######
    try:
        for i,row in enumerate(df.iter_rows(named=True)):
            record = RawSequence(
                source='Therapeutic Antibodies Database (SAbDab)',
                imported_at=datetime.utcnow(),
                ab_name=row['ab_name'],
                ab_format=row['ab_format'],
                ch1_isotype=row['ch1_isotype'],
                vd_lc=row['vd_lc'],
                heavy_chain1=row['heavy_chain1'],
                light_chain1=row['light_chain1'],
                heavy_chain2=row['heavy_chain2'],
                light_chain2=row['light_chain2'],
                target=row['target'],
                notes=row['notes'],
                genetics=row['genetics'],
                development_metadata={
                    'highest_clinical_phase': row['highest_clinical_phase'],
                    'dev_status': row['dev_status'],
                    'year_proposed': row['year_proposed'],
                    'year_recommended': row['year_recommended'],
                    'company': row['companies'],
                    'conditions_approved': row['conditions_approved'],
                    'conditions_active': row['conditions_active'],
                    'conditions_discontinued': row['conditions_discontinued'],
                    'dev_tech': row['dev_tech'],
                    'alt_therapeutic_uses': row['alt_therapeutic_uses']
                },
                structural_metadata={
                    'si_struct_100': row['si_struct_100'],
                    'si_struct_99': row['si_struct_99'],
                    'si_struct_95_98': row['si_struct_95_98']
                }
            )
            ####### DEV ONLY #######
            try:
                db.add(record)
                db.flush()
                inserted += 1
            except IntegrityError as ie:
                db.rollback()
                print(f"⚠️  Skipping duplicate entry for ab_name: {row['ab_name']}")
                skipped += 1
            ####### END DEV ONLY #######
            thera_records.append(record)
            # Show progress every 100 records
            if (i + 1) % 100 == 0:
                print(f"Prepared {i + 1}/{len(df)} records...")

        db.commit()
        print(f"✓ Ingestion complete. {inserted} records inserted, {skipped} records skipped due to duplicates.")
    except Exception as e:
        db.rollback()
        print(f"Error ingesting data from SAbDab: {e}")
        traceback.print_exc()
        raise
    finally:
        db.close()
    #### LATER - PRODUCTION BATCH INSERTION ####
    # try:
    #     db.bulk_save_objects(thera_records)
    #     db.commit()
    #     print(f"Inserted {len(thera_records)} records into 'staging.raw_sequences'.")
    # except Exception as e:
    #     db.rollback()
    #     print(f"Error inserting records: {e}")
    #     traceback.print_exc()
    #     raise
    # finally:
    #     db.close()

if __name__ == "__main__":
    load_sabdab_data()