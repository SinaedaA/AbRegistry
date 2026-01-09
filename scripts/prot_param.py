from Bio.SeqUtils.ProtParam import ProteinAnalysis
from database.models import ProteinProperties
import traceback
from scripts.utils import get_ab_chain_data, load_records_2_db
import polars as pl

def main(file_path='data/processed/sabdab_renamed.csv'):
    try:
        print("Generating Protein Properties annotations...")
        records = protein_properties(file_path)
        
        print("Loading annotations into database...")
        load_records_2_db(records)
        
        print("✅ All done!")
    except Exception as e:
        print(f"Error during Protein Properties calculation: {e}")
        traceback.print_exc()
        raise

def protein_properties(file_path: str):
    """
    Compute protein properties for antibody chains from a CSV file and return as ProteinProperties records.
    
    :param file_path: Path to the CSV file containing antibody sequences.
    :return: List of ProteinProperties records.
    """
    # Load sequences
    df = pl.read_csv(file_path)
    
    # Prepare sequences
    sequences_df = pl.concat([
        get_ab_chain_data(df, 'heavy_chain1'),
        get_ab_chain_data(df, 'heavy_chain2'),
        get_ab_chain_data(df, 'light_chain1'),
        get_ab_chain_data(df, 'light_chain2')
    ])
    
    # Compute protein properties
    records = create_protein_properties_records(sequences_df)
    
    return records

def create_protein_properties_records(sequences_df):
    records = []
    for row in sequences_df.iter_rows(named=True):
        seq = row['Sequence']
        properties = compute_protein_properties(seq)
        
        record = ProteinProperties(
            raw_sequence_id=None, ## added during ingestion
            ab_name=row['ab_name'],
            chain_name=row['chain_name'],
            chain_type=row['chain_type'],
            molecular_weight=properties['molecular_weight'],
            aromaticity=properties['aromaticity'],
            instability_index=properties['instability_index'],
            isoelectric_point=properties['isoelectric_point'],
            gravy=properties['gravy'],
            charge_at_ph7=properties['charge_at_pH7'],
            charge_at_ph5=properties['charge_at_pH5'],
            charge_at_ph9=properties['charge_at_pH9'],
            flexibility=properties['flexibility'],
            secondary_structure_hts={
                "helix": properties['secondary_structure_fraction'][0],
                "turn": properties['secondary_structure_fraction'][1],
                "sheet": properties['secondary_structure_fraction'][2]
            },
            amino_acid_counts=properties['aa_counts'],
            amino_acid_percent=properties['aa_percent'],
            molar_extinction_coeff={
                "reduced": properties['molar_extinction_coefficient'][0],
                "cysteine_bridges": properties['molar_extinction_coefficient'][1]
            }
        )
        records.append(record)
    return records

def compute_protein_properties(sequence: str) -> dict:
    analysis = ProteinAnalysis(sequence)
    properties = {
        'molecular_weight': analysis.molecular_weight(),
        'aromaticity': analysis.aromaticity(),
        'instability_index': analysis.instability_index(),
        'isoelectric_point': analysis.isoelectric_point(),
        'gravy': analysis.gravy(),
        'flexibility': analysis.flexibility(),
        'secondary_structure_fraction': analysis.secondary_structure_fraction(),
        'aa_counts': analysis.count_amino_acids(),
        'aa_percent': analysis.get_amino_acids_percent(),
        'charge_at_pH7': analysis.charge_at_pH(7.0),
        'charge_at_pH5': analysis.charge_at_pH(5.0),
        'charge_at_pH9': analysis.charge_at_pH(9.0),
        'molar_extinction_coefficient': analysis.molar_extinction_coefficient(),
    }
    return properties

if __name__ == "__main__":
    main()