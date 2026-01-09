from antpack import LiabilitySearchTool, SingleChainAnnotator
from database.models import Liabilities
import traceback
from scripts.utils import get_ab_chain_data, load_records_2_db
import polars as pl

def main(file_path: str = None):
    try:
        if file_path is None:
            # throw error and request file
            raise ValueError("Please provide a valid file path for the antibody sequences CSV.")
        
        print("Finding liabilities in antibody sequences...")
        records = find_liabilities(file_path)
        
        print("Loading liabilities into database...")
        load_records_2_db(records)
        
        print("✅ All done!")
    except Exception as e:
        print(f"Error during liability analysis: {e}")
        traceback.print_exc()
        raise

def find_liabilities(file_path: str):
    print("Loading sequences from CSV...")
    df = pl.read_csv(file_path)
    
    # Prepare sequences
    sequences = pl.concat([
        get_ab_chain_data(df, 'heavy_chain1'),
        get_ab_chain_data(df, 'heavy_chain2'),
        get_ab_chain_data(df, 'light_chain1'),
        get_ab_chain_data(df, 'light_chain2')
    ])

    print("Analyzing liabilities...")
    liabilities_df = analyze_liabilities_for_sequences(sequences)

    print("Preparing database records...")
    records = create_liability_records(liabilities_df)
    
    return records

def create_liability_records(liabilities_df):
    """
    Convert liabilities DataFrame to Liabilities records.
    
    :param liabilities_df: DataFrame with liability analysis results
    :return: List of Liabilities objects
    """
    records = []
    for row in liabilities_df.iter_rows(named=True):
        record = Liabilities(
            raw_sequence_id=None, ## added during ingestion
            ab_name=row['ab_name'].rsplit('_', 1)[0],
            chain_name=row['chain_name'],
            liability_type=row['liability_type'],
            start_position=row['start_position'],
            end_position=row['end_position'],
            motif_sequence=row['motif_sequence'],
            full_sequence_length=row['full_sequence_length']
        )
        records.append(record)
    return records

def analyze_liabilities_for_sequences(sequences_df):
    """
    Analyze liabilities for antibody sequences.
    
    :param sequences_df: DataFrame with 'Sequence', 'chain_name', 'chain_type'
    :return: DataFrame with liability results
    """
    annotator = SingleChainAnnotator(chains=['H', 'L', 'K'], scheme='imgt')
    liability_tool = LiabilitySearchTool()
    
    results = []
    
    for row in sequences_df.iter_rows(named=True):
        sequence = row['Sequence']
        chain_name = row['chain_name']
        
        try:
            # Number the sequence
            alignment = annotator.analyze_seq(sequence)
            
            # Search for liabilities
            liabilities = liability_tool.analyze_seq(
                sequence=sequence,
                alignment=alignment,
                scheme='imgt',
                cdr_scheme='imgt'
            )
            
            # Store results
            if liabilities:
                print(liabilities)
                for liability in liabilities:
                    position_range, liability_type = liability
                    start_pos, end_pos = position_range
                    motif = sequence[start_pos:end_pos+1]
                    
                    results.append({
                        'ab_name': row['ab_name'],
                        'chain_name': chain_name,
                        'liability_type': liability_type,
                        'start_position': start_pos,
                        'end_position': end_pos,
                        'motif_sequence': motif,
                        'full_sequence_length': len(sequence)
                    })
            else:
                # No liabilities found
                results.append({
                    'ab_name': row['ab_name'],
                    'chain_name': chain_name,
                    'liability_type': 'NONE',
                    'start_position': None,
                    'end_position': None,
                    'motif_sequence': None,
                    'full_sequence_length': len(sequence)
                })
                
        except Exception as e:
            print(f"⚠️  Failed to analyze {chain_name}: {e}")
            results.append({
                'ab_name': row['ab_name'],
                'chain_name': chain_name,
                'liability_type': 'ERROR',
                'start_position': None,
                'end_position': None,
                'motif_sequence': str(e),
                'full_sequence_length': len(sequence)
            })
    
    return pl.DataFrame(results)

if __name__ == "__main__":
    main()