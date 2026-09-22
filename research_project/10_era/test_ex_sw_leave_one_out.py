from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd

BASE = Path(r"D:\BANK\research_project")
ANALYSIS = BASE / '02_code' / 'analysis'
OUTDIR = BASE / '10_era'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

iv = load('inference_validation_era5', ANALYSIS / '09_INFERENCE_VALIDATION.py')
b = iv.b
panel_path = BASE / '01_data' / 'locked_inputs' / 'panel_master_FINAL.csv'
network_path = BASE / '01_data' / 'locked_inputs' / 'so_phong_chi_nhanh_FINAL.xlsx'

dr, dw, thresholds = b.build_analysis_data(panel_path, network_path)
idc = dw.columns[0]
comp = dw

raw_panel = pd.read_csv(panel_path)
sw = pd.ExcelFile(BASE / '01_data' / 'raw' / 'so phong chi nhanh.xlsx').parse('Phần mềm máy vi tính')
khauhao = sw[sw['Attribute.1'].str.contains('Khấu hao trong năm', na=False)].copy()
year_cols = [c for c in sw.columns if c not in ('Mã', 'Tên công ty', 'Attribute.1')]
long = khauhao.melt(id_vars=['Mã'], value_vars=year_cols, var_name='year', value_name='SW_khauhao')
long['year'] = long['year'].astype(int)
long = long.dropna(subset=['SW_khauhao'])
long['SW_khauhao_vnd'] = long['SW_khauhao'] * 1e6

merged = raw_panel.merge(long[['Mã', 'year', 'SW_khauhao_vnd']], on=['Mã', 'year'], how='left', validate='one_to_one')
merged['CI_raw'] = merged['opex'] / merged['ta']
merged['phys_ex_sw'] = merged['phys'].abs() - merged['SW_khauhao_vnd']
merged['AssetCostShare_ex_sw_raw'] = np.where(
    merged['CI_raw'] > 0, (merged['phys_ex_sw'] / merged['ta']) / merged['CI_raw'], np.nan)

comp = comp.merge(merged[[idc, 'year', 'AssetCostShare_ex_sw_raw']], on=[idc, 'year'], how='left', validate='one_to_one')

dprep, xvars = iv._prepare(comp, 'SW_stock', 'AssetCostShare_ex_sw_raw', False)
banks = sorted(dprep[idc].astype(str).unique())

def fit_row(dsub, omitted):
    X, y, resid, beta, inv, cols, groups = iv._fit(dsub, 'AssetCostShare_ex_sw_raw', xvars)
    cov = iv._covariances(X, resid, inv, groups)
    j = cols.index('z_X')
    se = float(np.sqrt(max(cov['cr2'][j, j], 0)))
    contrast = np.zeros(len(cols)); contrast[j] = 1
    df = iv._satterthwaite(cov['cr2'], inv, cov['qg'], contrast)
    t, p, lo, hi = iv._p_interval(float(beta[j]), se, df)
    wp, _, _, _ = iv._wild_bootstrap(X, y, beta, inv, cols, groups, 'z_X', B=999, seed=20260920)
    return dict(omitted=omitted, coef=float(beta[j]), p=p, df=df, N=cov['n'], G=cov['G'], wild_p=wp)

full = fit_row(dprep.copy(), '[FULL]')
print(f"FULL SAMPLE: coef={full['coef']:.6f}, CR2 p={full['p']:.6f}, df={full['df']:.4f}, wild p={full['wild_p']}")
print()

rows = []
for bank in banks:
    r = fit_row(dprep[dprep[idc].astype(str) != bank].copy(), bank)
    rows.append(r)

df_out = pd.DataFrame(rows)
df_out.to_csv(OUTDIR / 'ex_sw_leave_one_out.csv', index=False)

print('Coefficient range:', df_out['coef'].min(), '-', df_out['coef'].max())
print('CR2 p range:', df_out['p'].min(), '-', df_out['p'].max())
print('Banks where CR2 p < 0.05:', int((df_out['p'] < 0.05).sum()), '/', len(df_out))
print()
print(df_out.sort_values('p').to_string(index=False))
print('\nSaved:', OUTDIR / 'ex_sw_leave_one_out.csv')
