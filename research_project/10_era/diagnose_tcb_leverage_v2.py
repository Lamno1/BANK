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

iv = load('inference_validation_era7', ANALYSIS / '09_INFERENCE_VALIDATION.py')
b = iv.b
panel_path = BASE / '01_data' / 'locked_inputs' / 'panel_master_FINAL.csv'
network_path = BASE / '01_data' / 'locked_inputs' / 'so_phong_chi_nhanh_FINAL.xlsx'
dr, dw, thresholds = b.build_analysis_data(panel_path, network_path)
idc = dw.columns[0]
dprep, xvars = iv._prepare(dw, 'SW_stock', 'AssetCostShare_raw', False)

def influence_table(data, label):
    X, y, resid, beta, inv, cols, groups = iv._fit(data, 'AssetCostShare_raw', xvars)
    cov = iv._covariances(X, resid, inv, groups)
    j = cols.index('z_X')
    contrast = np.zeros(len(cols)); contrast[j] = 1
    df_correct = iv._satterthwaite(cov['cr2'], inv, cov['qg'], contrast)
    vjj = float(contrast @ cov['cr2'] @ contrast)
    rows = []
    for gkey, q in cov['qg'].items():
        infl = float(contrast @ inv @ q)
        rows.append((gkey, infl, infl**2))
    t = pd.DataFrame(rows, columns=['bank', 'influence', 'v_g'])
    t['share_of_variance'] = t['v_g'] / t['v_g'].sum()
    t = t.sort_values('v_g', ascending=False)
    check = 2 * (t['v_g'].sum()**2) / (t['v_g']**2).sum()
    print(f"\n{'='*78}\n{label}  (N={cov['n']}, G={cov['G']})")
    print(t.head(8).to_string(index=False))
    print(f"df (library _satterthwaite) = {df_correct:.4f}  |  df (manual v_g formula) = {check:.4f}  |  V_jj={vjj:.3e} vs sum(v_g)={t['v_g'].sum():.3e}")
    return t, df_correct

t_full, df_full = influence_table(dprep, 'FULL 26-bank sample')
t_notcb, df_notcb = influence_table(dprep[dprep[idc].astype(str) != 'TCB'].copy(), 'EXCLUDING TCB (25 banks)')
t_nombb, df_nombb = influence_table(dprep[dprep[idc].astype(str) != 'MBB'].copy(), 'EXCLUDING MBB (25 banks)')

print(f"\n{'='*78}\nSUMMARY")
print(f"Full sample df:        {df_full:.4f}")
print(f"Excluding TCB df:      {df_notcb:.4f}   (MBB share of variance: {t_notcb.set_index('bank').loc['MBB','share_of_variance']:.1%})")
print(f"Excluding MBB df:      {df_nombb:.4f}   (TCB share of variance: {t_nombb.set_index('bank').loc['TCB','share_of_variance']:.1%})")
