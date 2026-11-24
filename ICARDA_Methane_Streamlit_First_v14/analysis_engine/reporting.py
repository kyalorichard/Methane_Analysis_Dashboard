from io import BytesIO
import pandas as pd
def csv_bytes(df): return df.to_csv(index=False).encode("utf-8")
def excel_bytes(sheets):
    b=BytesIO()
    with pd.ExcelWriter(b,engine="openpyxl") as w:
        for name,df in sheets.items(): df.to_excel(w,sheet_name=name[:31],index=False)
    return b.getvalue()
