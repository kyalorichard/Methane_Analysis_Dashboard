import pandas as pd
from platform_core.species import infer_species_roles, get_profile
from platform_core.data_governance import inspect_dataset, validate_species_dataset

def test_sheep_adapter_maps_supplied_schema():
 cols=['AnimalID','Breed','Sex','weight','Round','file_date','mean_methane','recording_duration']
 roles=infer_species_roles(cols,'sheep')
 assert roles['animal_id']=='AnimalID'
 assert roles['methane']=='mean_methane'
 assert roles['recording_duration']=='recording_duration'

def test_species_profiles_are_distinct():
 assert get_profile('goat').key=='goat'
 assert get_profile('cattle').key=='cattle'
 assert get_profile('camel').key=='camel'

def test_dataset_profile_and_validation():
 df=pd.DataFrame({'AnimalID':['A','A'],'mean_methane':[1.2,1.4],'recording_duration':[180,200],'Round':['R1','R2']})
 p=inspect_dataset(df,'sheep')
 assert p['n_rows']==2 and p['n_animals']==1
 assert validate_species_dataset(df,'sheep')==[]
