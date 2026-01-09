import polars as pl
from antpack import SingleChainAnnotator
from database.models import AntpackAnnotation
from scripts.utils import get_ab_chain_data, load_records_2_db
import traceback

SABDAB_DB_PATH = 'data/processed/sabdab_renamed.csv'

def main(file_path=SABDAB_DB_PATH):
    try:
        print("Generating AntPack annotations...")
        records = antpack_annotation(file_path)
        
        print("Loading annotations into database...")
        load_records_2_db(records)
        
        print("✅ All done!")
    except Exception as e:
        print(f"Error during AntPack annotation process: {e}")
        traceback.print_exc()
        raise

def antpack_annotation(file_path=SABDAB_DB_PATH):
    """
    Load, annotate, and prepare AntPack records for database insertion.
    """
    print("Loading sequences from CSV...")
    df = pl.read_csv(file_path)
    
    # Prepare sequences
    sequences = pl.concat([
        get_ab_chain_data(df, 'heavy_chain1'),
        get_ab_chain_data(df, 'heavy_chain2'),
        get_ab_chain_data(df, 'light_chain1'),
        get_ab_chain_data(df, 'light_chain2')
    ])
    
    # Annotate
    annotated = annotate_sequences(sequences)
    
    # Convert to DB records
    records = create_antpack_records(annotated)
    
    return records

def annotate_sequences(sequences_df):
    """
    Annotate antibody sequences with CDR/framework regions.
    
    :param sequences_df: Polars DataFrame with 'Sequence' column
    :return: DataFrame with numbering and labelling columns
    """
    annotator = SingleChainAnnotator(chains=["H", "L", "K"], scheme="imgt")
    
    print("Adding numbering column...")
    sequences_df = sequences_df.with_columns([
        pl.col("Sequence").map_elements(
            lambda seq: annotator.analyze_seq(seq),
            return_dtype=pl.Object
        ).alias("numbering")
    ])
    
    print("Adding region labelling column...")
    sequences_df = sequences_df.with_columns([
        pl.col("numbering").map_elements(
            lambda num: annotator.assign_cdr_labels(numbering=num[0], chain=num[2]),
            return_dtype=pl.Object
        ).alias("labelling")
    ])
    
    return sequences_df

def create_antpack_records(annotated_df):
    """
    Convert annotated DataFrame to AntpackAnnotation records.
    
    :param annotated_df: DataFrame with numbering and labelling
    :return: List of AntpackAnnotation objects
    """
    ## Transform to match AntpackAnnotation model
    records = []
    for row in annotated_df.iter_rows(named=True):
        labelling = row['labelling']
        region_indices = find_region_indices(labelling) # (dictionary with fmwk1: (start,end), cdr1: (start,end), etc.)
        record = AntpackAnnotation(
            raw_sequence_id=None,  # to be linked later
            ab_name=row['ab_name'],
            chain_name=row['chain_name'],
            chain_type=row['chain_type'],
            numbering_scheme='imgt',
            numbering=row['numbering'][0],
            labelling=labelling,
            fmwk1_start=region_indices.get('fmwk1', (None, None))[0],
            fmwk1_end=region_indices.get('fmwk1', (None, None))[1],
            fmwk2_start=region_indices.get('fmwk2', (None, None))[0],
            fmwk2_end=region_indices.get('fmwk2', (None, None))[1],
            fmwk3_start=region_indices.get('fmwk3', (None, None))[0],
            fmwk3_end=region_indices.get('fmwk3', (None, None))[1],
            fmwk4_start=region_indices.get('fmwk4', (None, None))[0],
            fmwk4_end=region_indices.get('fmwk4', (None, None))[1],
            cdr1_start=region_indices.get('cdr1', (None, None))[0],
            cdr1_end=region_indices.get('cdr1', (None, None))[1],
            cdr2_start=region_indices.get('cdr2', (None, None))[0],
            cdr2_end=region_indices.get('cdr2', (None, None))[1],
            cdr3_start=region_indices.get('cdr3', (None, None))[0],
            cdr3_end=region_indices.get('cdr3', (None, None))[1]
        )
        records.append(record)
    
    return records

def find_region_indices(labels):
    """
    Docstring for find_region_indices. Used by extract_region_coordinates.

    :param labels: List of region labels from AntPack annotation
    :return: Dictionary with region names as keys and (start_idx, end_idx) tuples as values
    """
    regions = {}
    current_region = None
    start_idx = 0
    
    for idx, label in enumerate(labels):
        if label != current_region:
            if current_region is not None:
                regions[current_region] = (start_idx, idx)
            current_region = label
            start_idx = idx
    
    # Add the last region
    if current_region is not None:
        regions[current_region] = (start_idx, len(labels))
    
    return regions

if __name__ == "__main__":
    main()