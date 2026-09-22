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

iv = load('inference_validation_era2', ANALYSIS / '09_INFERENCE_VALIDATION.py')
b = iv.b
panel_path = BASE / '01_data' / 'locked_inputs' / 'panel_master_FINAL.csv'
network_path = BASE / '01_data' / 'locked_inputs' / 'so_phong_chi_nhanh_FINAL.xlsx'

dr, dw, thresholds = b.build_analysis_data(panel_path, network_path)
idc = dr.columns[0]
if dw.columns[0] != idc:
    dw = dw.rename(columns={dw.columns[0]: idc})
comp = dw if 'AssetCostShare_raw' in dw.columns else dw.merge(
    dr[[idc, 'year', 'AssetCostShare_raw', 'phys', 'ta', 'CI_raw' if 'CI_raw' in dr.columns else 'CI']],
    on=[idc, 'year'], how='left', validate='one_to_one')

# --- Build the software-amortization decomposition on the RAW (unwinsorized) accounting sample ---
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
    merged['CI_raw'] > 0,
    (merged['phys_ex_sw'] / merged['ta']) / merged['CI_raw'],
    np.nan)

comp = comp.merge(merged[[idc, 'year', 'AssetCostShare_ex_sw_raw', 'SW_khauhao_vnd']], on=[idc, 'year'], how='left', validate='one_to_one')

print('Rows with AssetCostShare_ex_sw_raw available:', comp['AssetCostShare_ex_sw_raw'].notna().sum(), '/', len(comp))

def fit(outcome_col, label):
    dprep, xvars = iv._prepare(comp, 'SW_stock', outcome_col, False)
    X, y, resid, beta, inv, cols, groups = iv._fit(dprep, outcome_col, xvars)
    cov = iv._covariances(X, resid, inv, groups)
    j = cols.index('z_X')
    se = float(np.sqrt(max(cov['cr2'][j, j], 0)))
    contrast = np.zeros(len(cols)); contrast[j] = 1
    df = iv._satterthwaite(cov['cr2'], inv, cov['qg'], contrast)
    t, p, lo, hi = iv._p_interval(float(beta[j]), se, df)
    print(f"\n{label}")
    print(f"  N={cov['n']}, G={cov['G']}, coef={beta[j]:.6f}, CR2 p={p:.6f}, df={df:.4f}, 95% CI=[{lo:.6f}, {hi:.6f}]")
    return dict(coef=float(beta[j]), p=p, df=df, N=cov['n'], G=cov['G'], lo=lo, hi=hi)

print('\n' + '='*78)
r_orig = fit('AssetCostShare_raw', 'ORIGINAL   SW_stock -> AssetCostShare_raw (locked primary spec, no branch_den)')
r_exsw = fit('AssetCostShare_ex_sw_raw', 'EX-SW      SW_stock -> AssetCostShare_ex_sw_raw (software amortization removed from AssetCost)')

comp.to_csv(OUTDIR / 'ex_software_comp_panel.csv', index=False)
print('\nSaved:', OUTDIR / 'ex_software_comp_panel.csv')
