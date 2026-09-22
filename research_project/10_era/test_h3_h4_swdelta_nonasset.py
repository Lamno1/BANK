from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd

BASE = Path(r"D:\BANK\research_project")
ANALYSIS = BASE / '02_code' / 'analysis'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

iv = load('iv_h3_h4', ANALYSIS / '09_INFERENCE_VALIDATION.py')
b = iv.b
panel_path = BASE / '01_data' / 'locked_inputs' / 'panel_master_FINAL.csv'
network_path = BASE / '01_data' / 'locked_inputs' / 'so_phong_chi_nhanh_FINAL.xlsx'
dr, dw, thresholds = b.build_analysis_data(panel_path, network_path)
idc = dw.columns[0]

raw_panel = pd.read_csv(panel_path)
sw = pd.ExcelFile(BASE / '01_data' / 'raw' / 'so phong chi nhanh.xlsx').parse('Phần mềm máy vi tính')
khauhao = sw[sw['Attribute.1'].str.contains('Khấu hao trong năm', na=False)].copy()
year_cols = [c for c in sw.columns if c not in ('Mã', 'Tên công ty', 'Attribute.1')]
long = khauhao.melt(id_vars=['Mã'], value_vars=year_cols, var_name='year', value_name='SW_khauhao')
long['year'] = long['year'].astype(int)
long = long.dropna(subset=['SW_khauhao'])
long['SW_khauhao_vnd'] = long['SW_khauhao'] * 1e6
merged = raw_panel.merge(long[['Mã', 'year', 'SW_khauhao_vnd']], on=['Mã', 'year'], how='left', validate='one_to_one')
merged['CI_ex_sw'] = (merged['opex'] - merged['SW_khauhao_vnd']) / merged['ta']
merged['CI_raw'] = merged['opex'] / merged['ta']
merged['AssetCost_ex_sw_raw'] = (merged['phys'].abs() - merged['SW_khauhao_vnd']) / merged['ta']
merged['AssetCostShare_ex_sw_raw'] = np.where(merged['CI_raw'] > 0, merged['AssetCost_ex_sw_raw'] / merged['CI_raw'], np.nan)
merged['NonAssetMinusAsset_ex_sw_raw'] = merged['CI_raw'] - 2 * merged['AssetCost_ex_sw_raw']
dw = dw.merge(merged[[idc, 'year', 'CI_ex_sw', 'AssetCostShare_ex_sw_raw', 'NonAssetMinusAsset_ex_sw_raw']],
              on=[idc, 'year'], how='left', validate='one_to_one')

def fit_report(d, outcome, xvars, focal, label):
    X, y, resid, beta, inv, cols, groups = iv._fit(d, outcome, xvars)
    cov = iv._covariances(X, resid, inv, groups)
    j = cols.index(focal)
    se = float(np.sqrt(max(cov['cr2'][j, j], 0)))
    contrast = np.zeros(len(cols)); contrast[j] = 1
    df = iv._satterthwaite(cov['cr2'], inv, cov['qg'], contrast)
    t, p, lo, hi = iv._p_interval(float(beta[j]), se, df)
    wp, _, _, _ = iv._wild_bootstrap(X, y, beta, inv, cols, groups, focal, B=999, seed=20260920)
    print(f"{label:45s} coef={beta[j]:+.6f}  CR2 p={p:.6f}  df={df:.3f}  wild p={wp}  N={cov['n']} G={cov['G']}")

print('='*100)
print('H3 -- SW_stock -> CI, original vs ex-software')
print('='*100)
d3, x3 = iv._prepare(dw, 'SW_stock', 'CI', False)
fit_report(d3, 'CI', x3, 'z_X', 'H3 SW_stock -> CI (original)')
d3b, x3b = iv._prepare(dw, 'SW_stock', 'CI_ex_sw', False)
fit_report(d3b, 'CI_ex_sw', x3b, 'z_X', 'H3 SW_stock -> CI_ex_sw')

print()
print('='*100)
print('H4 (SW_delta) -- Software net change -> AssetCostShare, original vs ex-software')
print('='*100)
d4d, x4d = iv._prepare(dw, 'SW_delta', 'AssetCostShare_raw', False)
fit_report(d4d, 'AssetCostShare_raw', x4d, 'z_X', 'H4 SW_delta -> AssetCostShare (original)')
d4de, x4de = iv._prepare(dw, 'SW_delta', 'AssetCostShare_ex_sw_raw', False)
fit_report(d4de, 'AssetCostShare_ex_sw_raw', x4de, 'z_X', 'H4 SW_delta -> AssetCostShare_ex_sw')

print()
print('='*100)
print('H4R-A -- NonAssetMinusAsset (absolute contrast), original vs ex-software, both digcols')
print('='*100)
for digcol in ['SW_stock', 'SW_delta']:
    da, xa = iv._prepare(dw, digcol, 'NonAssetMinusAsset_raw', False)
    fit_report(da, 'NonAssetMinusAsset_raw', xa, 'z_X', f'H4R-A {digcol} -> NonAssetMinusAsset (original)')
    dae, xae = iv._prepare(dw, digcol, 'NonAssetMinusAsset_ex_sw_raw', False)
    fit_report(dae, 'NonAssetMinusAsset_ex_sw_raw', xae, 'z_X', f'H4R-A {digcol} -> NonAssetMinusAsset_ex_sw')
