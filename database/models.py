from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, JSON, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database.database import Base

class RawSequence(Base):
    __tablename__ = 'raw_sequences'
    __table_args__ = (UniqueConstraint('source', 'ab_name', name='uix_source_ab_name'),
                      {'schema': 'staging'})

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False) # where the sequence was obtained from
    imported_at = Column(TIMESTAMP, default=datetime.utcnow)
    #ab_id = Column(String(50), nullable=False) # unique antibody identifier in the source
    ab_name = Column(String(50), nullable=False) # longest = 15
    ab_format = Column(String(200))
    ch1_isotype = Column(JSON)
    vd_lc = Column(JSON) # variable domain light chain type
    heavy_chain1 = Column(Text, nullable=False) # 140
    light_chain1 = Column(Text) # 115
    heavy_chain2 = Column(Text) # if bispecific antibody # 132
    light_chain2 = Column(Text) # if bispecific antibody # 113
    target = Column(JSON, nullable = False) # list of targets
    notes = Column(Text)
    genetics = Column(JSON) # genetic specification (humanised, genetically human, etc), bispecifics delimited with ;
    ## development metadata
    development_metadata = Column(JSON) # raw development metadata as obtained from source
    ## structural metadata
    structural_metadata = Column(JSON) # raw structural metadata as obtained from source
    functional_metadata = Column(JSON) # functional metadata for lab uploads, e.g. binding affinity, neutralization data, etc.
    manufacturing_metadata = Column(JSON) # manufacturing metadata for lab uploads, e.g. expression system, yield, stability in different conditions etc.

    ## Relationships
    antpack_annotations = relationship("AntpackAnnotation", back_populates="raw_sequence")
    protein_properties = relationship("ProteinProperties", back_populates="raw_sequence")
    liabilities = relationship("Liabilities", back_populates="raw_sequence")

class AntpackAnnotation(Base):
    __tablename__ = 'antpack_annotations'
    __table_args__ = {'schema': 'staging'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    ab_name = Column(String(50), nullable=False) # longest = 15
    chain_name = Column(String(60), nullable=False) # combination of ab_name + '_H' or '_L' (with 1 or 2 for bispecifics)
    chain_type = Column(String(10), nullable=False) # 'heavy' or 'light'
    numbering_scheme = Column(String(20), nullable=False) # e.g. 'chothia', 'imgt', etc.
    numbering = Column(JSON, nullable=False) # annotated sequence with numbering
    labelling = Column(JSON, nullable=False) # detailed annotations including region positions
    fmwk1_start = Column(Integer)
    fmwk1_end = Column(Integer)
    fmwk2_start = Column(Integer)
    fmwk2_end = Column(Integer)
    fmwk3_start = Column(Integer)
    fmwk3_end = Column(Integer)
    fmwk4_start = Column(Integer)
    fmwk4_end = Column(Integer)
    cdr1_start = Column(Integer)
    cdr1_end = Column(Integer)
    cdr2_start = Column(Integer)
    cdr2_end = Column(Integer)
    cdr3_start = Column(Integer)
    cdr3_end = Column(Integer)

    ## Relationships
    raw_sequence_id = Column(Integer, ForeignKey("staging.raw_sequences.id"))
    raw_sequence = relationship("RawSequence", back_populates="antpack_annotations")


class ProteinProperties(Base):
    __tablename__ = 'protein_properties'
    __table_args__ = {'schema': 'staging'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ab_name = Column(String(50), nullable=False)  # longest = 15
    chain_name = Column(String(60), nullable=False) # combination of ab_name + '_H' or '_L' (with 1 or 2 for bispecifics)
    chain_type = Column(String(10), nullable=False) # 'heavy' or 'light'
    
    # Scalar properties
    molecular_weight = Column(Float)  # mw
    aromaticity = Column(Float)  # arom
    instability_index = Column(Float)  # instability
    isoelectric_point = Column(Float)  # pI
    gravy = Column(Float)  # hydropathicity (GRAVY score)
    charge_at_ph7 = Column(Float)  # charge
    charge_at_ph5 = Column(Float)  # charge
    charge_at_ph9 = Column(Float)  # charge
    
    # Complex properties (stored as JSON)
    flexibility = Column(JSON)  # list of lists
    secondary_structure_hts = Column(JSON)  # tuple → store as {"helix": 0.x, "turn": 0.x, "sheet": 0.x}
    amino_acid_counts = Column(JSON)  # dict
    amino_acid_percent = Column(JSON)  # dict
    molar_extinction_coeff = Column(JSON)  # tuple → store as {"reduced": x, "cysteine_bridges": y}
    
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Relationship
    raw_sequence_id = Column(Integer, ForeignKey('staging.raw_sequences.id'), nullable=False)
    raw_sequence = relationship("RawSequence", back_populates="protein_properties")

class Liabilities(Base):
    __tablename__ = 'liabilities'
    __table_args__ = {'schema': 'staging'}
    
    id = Column(Integer, primary_key=True)
    ab_name = Column(String(50), nullable=False)  # longest = 15
    chain_name = Column(String(60))
    
    liability_type = Column(String(100))  # e.g., "N-glycosylation", "Oxidation"
    start_position = Column(Integer)
    end_position = Column(Integer)
    motif_sequence = Column(String(20))
    full_sequence_length = Column(Integer)
    
    computed_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Relationship
    raw_sequence_id = Column(Integer, ForeignKey('staging.raw_sequences.id'))
    raw_sequence = relationship("RawSequence", back_populates="liabilities")

class IngestionLog(Base):
    __tablename__ = 'ingestion_logs'
    __table_args__ = {'schema': 'staging'}
    
    run_id = Column(String(100), primary_key=True)
    source = Column(String(50), nullable=False)
    count = Column(Integer)
    status = Column(String(20))
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)