from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import date

# Valid amino acid alphabet
VALID_AA = set('ACDEFGHIKLMNPQRSTVWY')

class LabSequenceInput(BaseModel):
    """Validates incoming lab sequence data, but only core required fields and optional ones. Extra fields are allowed for different types of assay results in metadata."""
    class Config:
        extra = 'allow'  # Future-proof for new metadata
    
    # Required fields (no default value)
    ab_name: str = Field(..., min_length=1, max_length=50)
    heavy_chain1: str = Field(..., min_length=50)
    target: str
    company: str
    researcher: str
    project: str
    conditions_active: str
    upload_date: date
    
    # Semi-required (often present)
    ab_format: Optional[str] = Field(None, max_length=200)
    vd_lc: Optional[str] = None  # 'Lambda' or 'Kappa' only present when LC is there
    development_tech: Optional[str] = None # should usually be there, but not strictly required
    
    # Optional chains
    light_chain1: Optional[str] = Field(None, min_length=50) # optional with constraint
    heavy_chain2: Optional[str] = Field(None, min_length=50)  # For bispecifics
    light_chain2: Optional[str] = Field(None, min_length=50)  # For bispecifics
    
    # Optional metadata fields
    notes: Optional[str] = None
    genetics: Optional[str] = None
    ch1_isotype: Optional[str] = None
    
    # Validators
    @field_validator('heavy_chain1', 'light_chain1', 'heavy_chain2', 'light_chain2')
    @classmethod
    def validate_amino_acids(cls, v: str) -> str:
        """Check valid amino acid composition"""
        if v is None:
            return v
        
        invalid_chars = set(v.upper()) - VALID_AA
        if invalid_chars:
            raise ValueError(f'Invalid amino acid characters: {invalid_chars}')
        
        return v.upper()
    
    @field_validator('heavy_chain1', 'heavy_chain2')
    @classmethod
    def validate_heavy_length(cls, v: str) -> str:
        """Heavy chain should be 80-200 amino acids"""
        if v is None:
            return v
        
        if not (80 <= len(v) <= 200):
            raise ValueError(f'Heavy chain length {len(v)} outside expected range (80-200 AA)')
        
        return v
    
    @field_validator('light_chain1', 'light_chain2')
    @classmethod
    def validate_light_length(cls, v: str) -> str:
        """Light chain should be 70-150 amino acids"""
        if v is None:
            return v
        
        if not (70 <= len(v) <= 150):
            raise ValueError(f'Light chain length {len(v)} outside expected range (70-150 AA)')
        
        return v
    
    @field_validator('vd_lc')
    @classmethod
    def validate_vd_lc(cls, v: str) -> str:
        """Variable domain light chain must be Lambda or Kappa"""
        if v is None:
            return v
        
        if v not in ['Lambda', 'Kappa']:
            raise ValueError(f'vd_lc must be "Lambda" or "Kappa", got: {v}')
        
        return v
    
    ## Cross-validating fields (if vd_lc is present, light_chain1 must be present, and vice versa)
    @model_validator(mode = 'after') # validates after ALL fields are processed and assigned
    def check_light_chain_consistency(self) -> 'LabSequenceInput':
        """Validate after ALL fields are processed"""
        
        # If vd_lc specified, light chain must be present
        if self.vd_lc is not None and self.light_chain1 is None:
            raise ValueError('light_chain1 required when vd_lc is specified')
        
        # If light chain present, vd_lc should be specified
        if self.light_chain1 is not None and self.vd_lc is None:
            raise ValueError('vd_lc must be specified when light_chain1 is present')
        
        ## can add more conditions later, e.g., is bispecific, then several fields should be consistent with that (;-separated genetics, etc)

        return self  # Must return ALL values
    