import polars as pl
import random
from datetime import datetime, timedelta
import json
from antpack import SingleChainAnnotator
from scripts.antpack_annotation import find_region_indices

COMPANY_NAME = "ImmunoTech Labs"
RESEARCHERS = [
    "Dr. Alice Smith",
    "Dr. Bob Johnson",
    "Dr. Carol Williams",
    "Dr. David Brown",
    "Dr. Eve Davis"]
PROJECTS = [
    "Cancer Immunotherapy",
    "Autoimmune Disease Study",
    "Infectious Disease Response",
    "Vaccine Development",
    "Neurological Disorder Research"]
CONDITIONS_ACTIVE = [
    "Non-small cell lung cancer;Oesophageal cancer;Cancer;Solid tumours",
    "Autoimmune disorders;Crohn's disease;Rheumatoid arthritis",
    "Bacterial infections;Sepsis;Antibiotic resistance",
    "Viral infections;COVID-19;SARS-CoV-2",
    "Neurodegenerative diseases;Alzheimer's disease;Parkinson's disease"
]
#POTENTIAL_NAMES = json.load(open('data/lab_uploads/potential_antibody_names.json'))

def generate_lab_sequences(num_sequences=10, outfile='data/lab_uploads/simulated_lab_data.csv', ab_names = None):
    # 1. Read SAbDab data as templates
    df = pl.read_csv("data/raw/sabdab_summary.csv")
    # 2. Pick random sequences
    sampled_df = df.sample(n=num_sequences, with_replacement=False)
    # extract only HeavySequence and LightSequence columns
    sequences = sampled_df.select(["HeavySequence", "LightSequence", "Format", "Target", "Development Tech", "Genetics (Bispecifics delimited with semicolon)"])
    # 3. Annotate with AntPack
    vd_lcs_ann_seqs = antpack_annotation(sequences.select(["HeavySequence", "LightSequence"]))
    vd_lcs = vd_lcs_ann_seqs[0]
    annotated_sequences = vd_lcs_ann_seqs[1]
    # 4. Extract region coordinates
    region_coord_df = extract_region_coordinates(
        sequences=sequences,
        annotated_sequences=annotated_sequences,
        num_sequences=num_sequences,
        vd_lcs=vd_lcs)
    # 5. Mutate the CDR3 regions
    mutated_df = mutate_sequences(region_coord_df=region_coord_df)
    # 6. Add fake lab metadata
    simulated_lab_df = make_lab_data(df = mutated_df, ab_names = ab_names)
    # 7. Save as CSV
    simulated_lab_df.write_csv(outfile)

def antpack_annotation(sequences):
    """
    Docstring for antpack_annotation. Numbers sequences using IMGT scheme and assigns CDR and FMWK labels.

    :param sequences: DataFrame with sequences of light and heavy chains
    :return: List of annotated sequences from AntPack (interleaved heavy and light)
    """
    annotator = SingleChainAnnotator(chains=["H", "L", "K"], scheme="imgt")
    numbered_sequences = [annotator.analyze_seqs(seq_pair) for seq_pair in sequences.iter_rows()]
    
    annotated_sequences = [
        annotator.assign_cdr_labels(
            numbering=numbered_sequences[i][j][0], 
            chain=numbered_sequences[i][j][2]
        )
        for i in range(len(numbered_sequences))
        for j in [0, 1]  # Heavy then Light
    ]
    vd_lcs = [sub[2] for numbering in numbered_sequences for sub in numbering]
    
    return [vd_lcs, annotated_sequences]

def extract_region_coordinates(sequences, annotated_sequences, num_sequences, vd_lcs):
    """
    Docstring for extract_region_coordinates.

    :param sequences: DataFrame with sequences of light and heavy chains
    :param annotated_sequences: List of annotated sequences from AntPack
    :param num_sequences: Number of sequence pairs
    :return: DataFrame with region coordinates, for each sequence pair.
    """
    region_coord_data = []
    for seq_idx in range(num_sequences):
        heavy_idx = seq_idx * 2
        light_idx = heavy_idx + 1
        heavy_seq = sequences[seq_idx, 0]
        light_seq = sequences[seq_idx, 1]
        ab_format = sequences[seq_idx, 2]
        target = sequences[seq_idx, 3]
        dev_tech = sequences[seq_idx, 4]
        genetics = sequences[seq_idx, 5]
        vd_lc_short = vd_lcs[light_idx]
        vd_lc = 'Lambda' if vd_lc_short == 'L' else 'Kappa'
        
        heavy_regions = find_region_indices(annotated_sequences[heavy_idx])
        light_regions = find_region_indices(annotated_sequences[light_idx])
        region_coord_data.append({
            "heavy_sequence": heavy_seq,
            "light_sequence": light_seq,
            "ab_format": ab_format,
            "target": target,
            "vd_lc": vd_lc,
            "development_tech": dev_tech,
            "genetics": genetics,
            "heavy_cdr3_start": heavy_regions.get('cdr3', (None, None))[0],
            "heavy_cdr3_end": heavy_regions.get('cdr3', (None, None))[1],
            "light_cdr3_start": light_regions.get('cdr3', (None, None))[0],
            "light_cdr3_end": light_regions.get('cdr3', (None, None))[1]
            # "fmwk1_coords": [heavy_regions.get('fmwk1', (None, None))] + [light_regions.get('fmwk1', (None, None))], ETCTEREA IF NEEDED
        })
    return pl.DataFrame(region_coord_data)

def mutate_sequences(region_coord_df):
    """
    Docstring for mutate_sequences
    
    :param region_coord_df: DataFrame with sequences of light and heavy chains, and their CDR3 region coordinates. 
    :return: DataFrame with mutated sequences.
    """
    mutated_sequences = []
    for row in region_coord_df.iter_rows(named = True):
        heavy_mutated = mutate_cdr3(
            seq=row["heavy_sequence"],
            cdr3_start=row["heavy_cdr3_start"],
            cdr3_end=row["heavy_cdr3_end"])
        light_mutated = mutate_cdr3(
            seq=row["light_sequence"],
            cdr3_start=row["light_cdr3_start"],
            cdr3_end=row["light_cdr3_end"])
        mutated_sequences.append({
            "ab_format": row["ab_format"],
            "target": row["target"],
            "vd_lc": row["vd_lc"],
            "development_tech": row["development_tech"],
            "genetics": row["genetics"],
            'heavy_chain1': heavy_mutated,
            'light_chain1': light_mutated,
            'notes': f"Mutated CDR3 from SAbDab {row['ab_format']} template."
        })
    return pl.DataFrame(mutated_sequences)

def mutate_cdr3(seq, cdr3_start, cdr3_end, num_mutations=3):
    """
    Docstring for mutate_cdr3, used by mutate_sequences.
    
    :param seq: Amino acid sequence string
    :param cdr3_start: Start index of CDR3 region
    :param cdr3_end: End index of CDR3 region
    :param num_mutations: Number of mutations to introduce within CDR3 region
    :return: Mutated amino acid sequence string
    """
    if cdr3_start is None or cdr3_end is None:
        return seq  # Can't mutate if CDR3 not found
    
    aa_alphabet = list('ACDEFGHIKLMNPQRSTVWY')
    seq_list = list(seq)
    
    # Only mutate within CDR3
    cdr3_positions = list(range(cdr3_start, cdr3_end))
    positions_to_mutate = random.sample(
        cdr3_positions,
        min(num_mutations, len(cdr3_positions))
    )
    
    for pos in positions_to_mutate:
        original_aa = seq_list[pos]
        new_aa = random.choice([aa for aa in aa_alphabet if aa != original_aa])
        seq_list[pos] = new_aa
    
    return ''.join(seq_list)

def make_lab_data(df, ab_names = None):
    """
    Docstring for make_lab_data
    
    :param df: Dataframe to which to add random project metadata
    :return: Dataframe with added project metadata
    """
    final_data = []
    idx = random.randint(0, len(PROJECTS)-1) # pick a random project and researcher for all sequences (and use the same company for all)
    for row in df.iter_rows(named = True):
        company = COMPANY_NAME
        researcher = RESEARCHERS[idx]
        project = PROJECTS[idx]
        conditions_active = CONDITIONS_ACTIVE[idx]
        upload_date = datetime.now() - timedelta(days=random.randint(0, 30))
        final_data.append({
            "ab_name": ab_names.pop() if ab_names else f"LAB_AB_{random.randint(10000,99999)}",
            **row,
            "company": company,
            "researcher": researcher,
            "project": project,
            "conditions_active": conditions_active,
            "upload_date": upload_date.strftime("%Y-%m-%d")
        })
    df = pl.DataFrame(final_data)
    print(f"{researcher} generated {len(df)} new antibody sequences for project {project}. Company: {company}.")
    return df

if __name__ == "__main__":
    generate_lab_sequences(10)