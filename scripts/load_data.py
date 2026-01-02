import polars as pl
from database.database import SessionLocal, engine
from database.models import RawSequence
from datetime import datetime
import traceback

def main():
    print("Loading initial data into 'staging.raw_sequences' table...")
    
    # Example: Load data from a CSV file using Polars
    df = pl.read_csv('data/raw/sabdab_summary.csv')
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
    # Convert Polars DataFrame to list of RawSequence objects
    thera_records = []
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
                'companies': row['companies'],
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
        thera_records.append(record)
        # Show progress every 100 records
        if (i + 1) % 100 == 0:
            print(f"Prepared {i + 1}/{len(df)} records...")
    
    # Insert records into the database
    db = SessionLocal()
    try:
        db.bulk_save_objects(thera_records)
        db.commit()
        print(f"Inserted {len(thera_records)} records into 'staging.raw_sequences'.")
    except Exception as e:
        db.rollback()
        print(f"Error inserting records: {e}")
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()