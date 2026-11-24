from io import BytesIO
import pandas as pd
import pytest
from analysis_engine.io import load_uploaded_data, dataframe_to_parquet_bytes

class Upload:
    def __init__(self,name,payload): self.name=name; self._payload=payload
    def getvalue(self): return self._payload

def test_csv_upload_loads_dataframe():
    raw=b"AnimalID,mean_methane\nA1,12.5\nA2,14.0\n"
    df=load_uploaded_data(Upload("study.csv",raw))
    assert list(df.columns)==["AnimalID","mean_methane"] and len(df)==2

def test_parquet_upload_loads_dataframe():
    original=pd.DataFrame({"AnimalID":["A1","A2"],"mean_methane":[12.5,14.0]})
    raw=dataframe_to_parquet_bytes(original)
    loaded=load_uploaded_data(Upload("study.parquet",raw))
    pd.testing.assert_frame_equal(loaded,original)

def test_pq_extension_supported():
    original=pd.DataFrame({"id":[1,2],"ch4":[1.2,1.4]})
    loaded=load_uploaded_data(Upload("study.pq",dataframe_to_parquet_bytes(original)))
    pd.testing.assert_frame_equal(loaded,original)

def test_unsupported_extension_rejected():
    with pytest.raises(ValueError): load_uploaded_data(Upload("study.json",b"{}"))
