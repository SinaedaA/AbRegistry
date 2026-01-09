import polars as pl
from database.database import SessionLocal
from database.models import RawSequence
import traceback

def get_ab_chain_data(df, chain_type):
    chain_suffix = f"{chain_type[0]}{chain_type[-1]}"
    
    if chain_type not in df.columns:
        return pl.DataFrame(schema={
            "ab_name": pl.Utf8, 
            "Sequence": pl.Utf8, 
            "chain_name": pl.Utf8, 
            "chain_type": pl.Utf8
        })
    
    ab_chain_data = (df
        .select(['ab_name', chain_type])
        .filter(pl.col(chain_type) != "na")
        .filter(pl.col(chain_type).is_not_null())
        .with_columns(
            (pl.col("ab_name") + f"_{chain_suffix}").alias("chain_name"),
            pl.lit("heavy" if 'heavy' in chain_type else "light").alias("chain_type"),
        )
        .rename({chain_type: "Sequence"})
    )
    
    return ab_chain_data

def load_records_2_db(records=None):
    """
    Loads protein annotation records (from Antpack or ProtParam) into the database for antibody sequences.
    """
    # Insert records into the database
    db = SessionLocal()
    try:
        # Get all ab_names we need to link
        ab_names = list(set([r.ab_name for r in records]))
        
        # Query all matching RawSequences at once
        raw_seqs = db.query(RawSequence).filter(
            RawSequence.ab_name.in_(ab_names)
            #RawSequence.source == 'Therapeutic Antibodies Database (SAbDab)'
        ).all()
        
        # Create lookup dict
        raw_seq_lookup = {rs.ab_name: rs.id for rs in raw_seqs}
        
        # Link annotations
        for record in records:
            record.raw_sequence_id = raw_seq_lookup.get(record.ab_name)
            
            if record.raw_sequence_id is None:
                print(f"⚠️  No match for {record.ab_name}")
        
        db.bulk_save_objects(records)
        db.commit()
        print(f"Inserted {len(records)} annotations")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        traceback.print_exc()
        raise
    finally:
        db.close()