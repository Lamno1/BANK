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

iv = load('iv_flow_diag', ANALYSIS / '09_INFERENCE_VALIDATION.py')
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

D2, x2 = b.prep_fi(dw, 'SW_delta', required_outcomes=('CI', 'CI_ex_sw'))
D2 = D2.copy()
D2['Post'] = (D2['year'] >= 2020).astype(int)
D2['digxpost'] = D2['z_FI_dig'] * D2['Post']
D2['tradxpost'] = D2['z_FI_trad'] * D2['Post']
xt = ['z_FI_dig', 'z_FI_trad', 'digxpost', 'tradxpost'] + ['z_' + c for c in b.CTRL]

def influence_table(outcome, label):
    X, y, resid, beta, inv, cols, groups = iv._fit(D2, outcome, xt)
    cov = iv._covariances(X, resid, inv, groups)
    j = cols.index('digxpost')
    contrast = np.zeros(len(cols)); contrast[j] = 1
    df = iv._satterthwaite(cov['cr2'], inv, cov['qg'], contrast)
    rows = []
    for gkey, q in cov['qg'].items():
        infl = float(contrast @ inv @ q)
        rows.append((gkey, infl, infl ** 2))
    t = pd.DataFrame(rows, columns=['bank', 'influence', 'v_g'])
    t['share_of_variance'] = t['v_g'] / t['v_g'].sum()
    t = t.sort_values('v_g', ascending=False)
    print(f"\n{'='*78}\n{label} (N={cov['n']}, G={cov['G']}, df={df:.4f}, coef={beta[j]:+.6f})")
    print(t.head(8).to_string(index=False))
    return t, df

t_orig, df_orig = influence_table('CI', 'ORIGINAL CI, digxpost (Flow x Post2020)')
t_exsw, df_exsw = influence_table('CI_ex_sw', 'EX-SOFTWARE CI, digxpost (Flow x Post2020)')

print(f"\n{'='*78}\nSUMMARY: df original={df_orig:.4f} -> df ex-sw={df_exsw:.4f}")
top_orig = t_orig.iloc[0]['bank']; top_exsw = t_exsw.iloc[0]['bank']
print(f"Top-influence cluster ORIGINAL: {top_orig} ({t_orig.iloc[0]['share_of_variance']:.1%})")
print(f"Top-influence cluster EX-SW:    {top_exsw} ({t_exsw.iloc[0]['share_of_variance']:.1%})")
merged_shares = t_orig[['bank','share_of_variance']].merge(t_exsw[['bank','share_of_variance']], on='bank', suffixes=('_orig','_exsw'))
merged_shares['delta'] = merged_shares['share_of_variance_exsw'] - merged_shares['share_of_variance_orig']
print("\nBiggest share increases (original -> ex-sw):")
print(merged_shares.sort_values('delta', ascending=False).head(6).to_string(index=False))
