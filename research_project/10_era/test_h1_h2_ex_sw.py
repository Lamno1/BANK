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

iv = load('iv_h1_h2', ANALYSIS / '09_INFERENCE_VALIDATION.py')
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
dw = dw.merge(merged[[idc, 'year', 'CI_ex_sw']], on=[idc, 'year'], how='left', validate='one_to_one')

def fit_report(d, outcome, xvars, focal, label):
    X, y, resid, beta, inv, cols, groups = iv._fit(d, outcome, xvars)
    cov = iv._covariances(X, resid, inv, groups)
    j = cols.index(focal)
    se = float(np.sqrt(max(cov['cr2'][j, j], 0)))
    contrast = np.zeros(len(cols)); contrast[j] = 1
    df = iv._satterthwaite(cov['cr2'], inv, cov['qg'], contrast)
    t, p, lo, hi = iv._p_interval(float(beta[j]), se, df)
    wp, _, _, _ = iv._wild_bootstrap(X, y, beta, inv, cols, groups, focal, B=999, seed=20260920)
    print(f"{label:40s} coef={beta[j]:+.6f}  CR2 p={p:.6f}  df={df:.3f}  wild p={wp}  N={cov['n']} G={cov['G']}")

print('='*100)
print('H1 -- CASA baseline -> CI, original vs ex-software')
print('='*100)
D, x = b.prep_fi(dw, 'CASA', required_outcomes=('CI', 'CI_ex_sw'))
fit_report(D, 'CI', x, 'z_FI_dig', 'H1 CASA -> CI (original)')
fit_report(D, 'CI_ex_sw', x, 'z_FI_dig', 'H1 CASA -> CI_ex_sw (ex-software)')

print()
print('='*100)
print('H2 -- Flow baseline and Flow x Post-2020 -> CI, original vs ex-software')
print('='*100)
D2, x2 = b.prep_fi(dw, 'SW_delta', required_outcomes=('CI', 'CI_ex_sw'))
fit_report(D2, 'CI', x2, 'z_FI_dig', 'H2 Flow baseline -> CI (original)')
fit_report(D2, 'CI_ex_sw', x2, 'z_FI_dig', 'H2 Flow baseline -> CI_ex_sw (ex-sw)')

D2 = D2.copy()
D2['Post'] = (D2['year'] >= 2020).astype(int)
D2['digxpost'] = D2['z_FI_dig'] * D2['Post']
D2['tradxpost'] = D2['z_FI_trad'] * D2['Post']
xt = ['z_FI_dig', 'z_FI_trad', 'digxpost', 'tradxpost'] + ['z_' + c for c in b.CTRL]
fit_report(D2, 'CI', xt, 'digxpost', 'H2 Flow x Post2020 -> CI (original)')
fit_report(D2, 'CI_ex_sw', xt, 'digxpost', 'H2 Flow x Post2020 -> CI_ex_sw (ex-sw)')
