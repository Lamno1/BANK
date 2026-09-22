import pandas as pd
import numpy as np

RAW = r"D:\BANK\research_project\01_data\raw\so phong chi nhanh.xlsx"
PANEL = r"D:\BANK\research_project\01_data\locked_inputs\panel_master_FINAL.csv"
OUT = r"D:\BANK\research_project\10_era\sw_amort_decomposition.csv"

sw = pd.ExcelFile(RAW).parse('Phần mềm máy vi tính')
khauhao = sw[sw['Attribute.1'].str.contains('Khấu hao trong năm', na=False)].copy()
year_cols = [c for c in sw.columns if c not in ('Mã', 'Tên công ty', 'Attribute.1')]

long = khauhao.melt(id_vars=['Mã'], value_vars=year_cols, var_name='year', value_name='SW_khauhao')
long['year'] = long['year'].astype(int)
long = long.dropna(subset=['SW_khauhao'])

panel = pd.read_csv(PANEL)
merged = panel.merge(long, on=['Mã', 'year'], how='left', validate='one_to_one')

print('Panel rows:', len(panel))
print('Rows with SW_khauhao matched:', merged['SW_khauhao'].notna().sum())
print('Rows missing SW_khauhao:', merged['SW_khauhao'].isna().sum())
missing = merged[merged['SW_khauhao'].isna()][['Mã', 'year']]
print('Missing bank-years (first 20):')
print(missing.head(20).to_string())
print()
print('Distinct banks missing entirely:', sorted(missing['Mã'].unique()))

# Sanity check against known calibration points
for t, y, expected in [('TCB', 2018, 0.0886), ('VPB', 2018, 0.0771)]:
    row = merged[(merged['Mã'] == t) & (merged['year'] == y)]
    if len(row):
        share = float(row['SW_khauhao'].iloc[0]) / float(row['phys'].iloc[0])
        print(f'{t} {y}: SW_khauhao/phys = {share:.4%} (prior calibration: {expected:.2%})')

merged.to_csv(OUT, index=False)
print('\nSaved:', OUT)
