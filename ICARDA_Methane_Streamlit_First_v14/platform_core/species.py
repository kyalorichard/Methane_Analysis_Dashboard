from dataclasses import dataclass, asdict
from typing import Optional

@dataclass(frozen=True)
class SpeciesProfile:
    key: str
    label: str
    animal_id_aliases: tuple[str,...]
    group_aliases: tuple[str,...]
    sex_aliases: tuple[str,...]
    weight_aliases: tuple[str,...]
    session_aliases: tuple[str,...]
    date_aliases: tuple[str,...]
    methane_signal_aliases: tuple[str,...]
    duration_aliases: tuple[str,...]
    note: str

PROFILES={
 'sheep': SpeciesProfile('sheep','Sheep',('AnimalID','animal_id','Animal_ID','EID'),('Breed','breed','Genotype'),('Sex','sex','Gender'),('weight','Weight','BodyWeight','body_weight'),('Round','round','Session','Visit'),('file_date','date','Date','measurement_date'),('mean_methane','Methane_Mean','CH4_mean','mean_CH4','AUC_full','AUC'),('recording_duration','duration','recording_duration_sec','Duration_sec'),'Sheep adapter aligned to the supplied ICARDA methane phenotype data; verify instrument and protocol metadata.'),
 'goat': SpeciesProfile('goat','Goat',('AnimalID','animal_id','Animal_ID','EID'),('Breed','breed','Genotype'),('Sex','sex','Gender'),('weight','Weight','BodyWeight','body_weight'),('Round','round','Session','Visit'),('date','Date','measurement_date','file_date'),('mean_methane','Methane_Mean','CH4_mean','mean_CH4','AUC_full','AUC'),('recording_duration','duration','recording_duration_sec','Duration_sec'),'Goat-specific measurement protocol, instrument calibration and phenotype definitions must be configured for each study.'),
 'cattle': SpeciesProfile('cattle','Cattle',('AnimalID','animal_id','Animal_ID','EID','CowID'),('Breed','breed','Genotype'),('Sex','sex','Gender'),('weight','Weight','BodyWeight','body_weight'),('Round','round','Session','Visit','TestDate'),('date','Date','measurement_date','file_date'),('mean_methane','Methane_Mean','CH4_mean','mean_CH4','CH4_ppm','CH4_g_day','AUC_full','AUC'),('recording_duration','duration','recording_duration_sec','Duration_sec'),'Cattle systems may use breath, chamber, GreenFeed or laser measurements; retain method-specific units and calibration.'),
 'buffalo': SpeciesProfile('buffalo','Buffalo',('AnimalID','animal_id','Animal_ID','EID'),('Breed','breed','Genotype'),('Sex','sex','Gender'),('weight','Weight','BodyWeight','body_weight'),('Round','round','Session','Visit'),('date','Date','measurement_date','file_date'),('mean_methane','Methane_Mean','CH4_mean','mean_CH4','CH4_g_day','AUC_full','AUC'),('recording_duration','duration','recording_duration_sec','Duration_sec'),'Buffalo-specific protocol and calibration metadata are required.'),
 'camel': SpeciesProfile('camel','Camel',('AnimalID','animal_id','Animal_ID','EID','CamelID'),('Breed','breed','Type','Genotype'),('Sex','sex','Gender'),('weight','Weight','BodyWeight','body_weight'),('Round','round','Session','Visit'),('date','Date','measurement_date','file_date'),('mean_methane','Methane_Mean','CH4_mean','mean_CH4','CH4_g_day','AUC_full','AUC'),('recording_duration','duration','recording_duration_sec','Duration_sec'),'Camel-specific measurement protocol and validated phenotype definitions are required.'),
 'other': SpeciesProfile('other','Other livestock',('AnimalID','animal_id','Animal_ID','EID','ID'),('Breed','breed','Genotype','Group'),('Sex','sex','Gender'),('weight','Weight','BodyWeight','body_weight'),('Round','round','Session','Visit'),('date','Date','measurement_date','file_date'),('mean_methane','Methane_Mean','CH4_mean','mean_CH4','AUC_full','AUC'),('recording_duration','duration','recording_duration_sec','Duration_sec'),'Define and approve a study-specific adapter before inferential or cross-species analyses.'),
}

def get_profile(species:str)->SpeciesProfile:
 key=(species or 'other').strip().lower()
 return PROFILES.get(key,PROFILES['other'])

def infer_species_roles(columns, species):
 p=get_profile(species)
 cols=list(columns)
 aliases={
  'animal_id':p.animal_id_aliases,'breed':p.group_aliases,'sex':p.sex_aliases,
  'weight':p.weight_aliases,'round':p.session_aliases,'date':p.date_aliases,
  'methane':p.methane_signal_aliases,'recording_duration':p.duration_aliases,
 }
 out={}
 for role,names in aliases.items():
  out[role]=next((c for c in cols if c in names),None)
 return out

def profile_dict(species):
 return asdict(get_profile(species))
