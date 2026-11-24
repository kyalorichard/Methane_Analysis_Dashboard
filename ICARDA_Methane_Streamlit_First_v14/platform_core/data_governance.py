import hashlib
import pandas as pd
from platform_core.species import infer_species_roles, get_profile

def sha256_bytes(data:bytes)->str:
 return hashlib.sha256(data).hexdigest()

def inspect_dataset(df:pd.DataFrame,species:str)->dict:
 roles=infer_species_roles(df.columns,species)
 profile=get_profile(species)
 numeric=df.select_dtypes(include='number')
 return {
  'species':profile.key,'species_label':profile.label,'n_rows':int(len(df)),
  'n_columns':int(df.shape[1]),'n_animals':int(df[roles['animal_id']].nunique()) if roles.get('animal_id') else None,
  'missing_cells':int(df.isna().sum().sum()),
  'missing_percent':round(float(df.isna().mean().mean()*100),3) if df.size else 0.0,
  'duplicate_rows':int(df.duplicated().sum()),
  'roles':roles,
  'candidate_numeric_variables':numeric.columns.tolist(),
  'species_adapter_note':profile.note,
  'requires_protocol_review':True,
 }

def validate_species_dataset(df:pd.DataFrame,species:str)->list[str]:
 r=infer_species_roles(df.columns,species)
 issues=[]
 if not r.get('animal_id'): issues.append('Animal identifier was not detected. Map a stable animal ID before repeated-measures analysis.')
 if not r.get('methane'): issues.append('No candidate methane signal variable was detected. Map a measurement variable and document its units and calibration.')
 if not r.get('recording_duration'): issues.append('Recording duration was not detected. Duration-based QC will be unavailable.')
 if not r.get('round') and not r.get('date'): issues.append('No repeated session or measurement date was detected. Longitudinal/repeatability modules may not be applicable.')
 return issues
