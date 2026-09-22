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

iv = load('iv_h4a_h5', ANALYSIS / '09_INFERENCE_VALIDATION.py')
b = iv.b
panel_path = BASE / '01_data' / 'locked_inputs' / 'panel_master_FINAL.csv'
network_path = BASE / '01_data' / 'locked_inputs' / 'so_phong_chi_nhanh_FINAL.xlsx'

dr, dw, thresholds = b.build_analysis_data(panel_path, network_path)
idc = dw.columns[0]

# --- Build ex-sw CI (aggregate cost intensity net of the software-amortization line) ---
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
    print(f"{label:45s} coef={beta[j]:+.6f}  CR2 p={p:.6f}  df={df:.3f}  wild p={wp}  N={cov['n']} G={cov['G']}")
    return dict(coef=float(beta[j]), p=p, df=df, wild_p=wp, N=cov['n'], G=cov['G'])

print('='*100)
print('H5 -- Stock x BIG_it and Stock x continuous lnTA, ORIGINAL CI vs EX-SW CI')
print('='*100)

BIG_THRESHOLD = dw['lnTA'].median()
D, x = b.prep_fi(dw, 'SW_stock', required_outcomes=('CI', 'CI_ex_sw'))
D = D.copy()
D['BIG'] = (D['lnTA'] > BIG_THRESHOLD).astype(int)
D['DxBIG'] = D['z_FI_dig'] * D['BIG']
x5 = ['z_FI_dig', 'BIG', 'DxBIG', 'z_FI_trad'] + ['z_' + c for c in b.CTRL]
fit_report(D, 'CI', x5, 'DxBIG', 'H5 Stock x BIG_it -> CI (original)')
fit_report(D, 'CI_ex_sw', x5, 'DxBIG', 'H5 Stock x BIG_it -> CI_ex_sw (ex-software)')

D['FIxlnTA'] = D['z_FI_dig'] * D['z_lnTA']
x5b = ['z_FI_dig', 'FIxlnTA', 'z_FI_trad'] + ['z_' + c for c in b.CTRL]
fit_report(D, 'CI', x5b, 'FIxlnTA', 'H5 Stock x continuous lnTA -> CI (original)')
fit_report(D, 'CI_ex_sw', x5b, 'FIxlnTA', 'H5 Stock x continuous lnTA -> CI_ex_sw (ex-software)')

print()
print('='*100)
print('H4a -- Stock -> ln(network), cluster-influence decomposition (why CR2 significant but wild is not)')
print('='*100)

Dn = dw.replace([np.inf, -np.inf], np.nan).dropna(subset=['SW_stock', 'network_count_harmonized'] + b.CTRL).copy()
Dn = Dn[Dn['network_count_harmonized'] > 0].copy()
Dn['lnNetworkCount_raw'] = np.log(Dn['network_count_harmonized'])
Dn['FI_dig'] = b.mm(Dn['SW_stock']); Dn['z_FI_dig'] = b.z(Dn['FI_dig'])
for c in b.CTRL: Dn['z_' + c] = b.z(Dn[c])
xn = ['z_FI_dig'] + ['z_' + c for c in b.CTRL]

X, y, resid, beta, inv, cols, groups = iv._fit(Dn, 'lnNetworkCount_raw', xn)
cov = iv._covariances(X, resid, inv, groups)
j = cols.index('z_FI_dig')
contrast = np.zeros(len(cols)); contrast[j] = 1
df_h4a = iv._satterthwaite(cov['cr2'], inv, cov['qg'], contrast)
se = float(np.sqrt(max(cov['cr2'][j, j], 0)))
t, p, lo, hi = iv._p_interval(float(beta[j]), se, df_h4a)
wp, _, _, _ = iv._wild_bootstrap(X, y, beta, inv, cols, groups, 'z_FI_dig', B=999, seed=20260920)
print(f"Full sample: coef={beta[j]:+.6f}  CR2 p={p:.6f}  df={df_h4a:.3f}  wild p={wp}  N={cov['n']} G={cov['G']}")

rows = []
for gkey, q in cov['qg'].items():
    infl = float(contrast @ inv @ q)
    rows.append((gkey, infl, infl ** 2))
t_h4a = pd.DataFrame(rows, columns=['bank', 'influence', 'v_g'])
t_h4a['share_of_variance'] = t_h4a['v_g'] / t_h4a['v_g'].sum()
t_h4a = t_h4a.sort_values('v_g', ascending=False)
print(t_h4a.head(8).to_string(index=False))
t_h4a.to_csv(BASE / '10_era' / 'h4a_influence_full_sample.csv', index=False)
print('\nSaved: h4a_influence_full_sample.csv')
