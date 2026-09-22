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

iv = load('inference_validation_era6', ANALYSIS / '09_INFERENCE_VALIDATION.py')
b = iv.b
panel_path = BASE / '01_data' / 'locked_inputs' / 'panel_master_FINAL.csv'
network_path = BASE / '01_data' / 'locked_inputs' / 'so_phong_chi_nhanh_FINAL.xlsx'

dr, dw, thresholds = b.build_analysis_data(panel_path, network_path)
idc = dw.columns[0]
comp = dw

dprep, xvars = iv._prepare(comp, 'SW_stock', 'AssetCostShare_raw', False)

# --- 1. Exposure diagnostics: is TCB an outlier in z_X (standardized SW_stock)? ---
print('='*78)
print('1. z_X (standardized SW_stock) by bank -- mean, count, max|z_X|')
g = dprep.groupby(idc)['z_X'].agg(['mean', 'std', 'count', lambda s: s.abs().max()])
g.columns = ['mean_zX', 'sd_zX', 'n_obs', 'max_abs_zX']
g = g.sort_values('max_abs_zX', ascending=False)
print(g.head(10).to_string())
print()
print('TCB row:')
print(g.loc[['TCB']].to_string() if 'TCB' in g.index else 'TCB not found')

# --- 2. Per-cluster CR2 influence on the Satterthwaite df, WITH TCB (full 26-cluster sample) ---
X, y, resid, beta, inv, cols, groups = iv._fit(dprep, 'AssetCostShare_raw', xvars)
cov = iv._covariances(X, resid, inv, groups)
j = cols.index('z_X')
contrast = np.zeros(len(cols)); contrast[j] = 1

infl_full = {}
for gkey, q in cov['qg'].items():
    infl_full[gkey] = float(contrast @ inv @ q)

infl_df = pd.DataFrame({'bank': list(infl_full.keys()), 'influence': list(infl_full.values())})
infl_df['influence_sq'] = infl_df['influence'] ** 2
infl_df['share_of_total_sq'] = infl_df['influence_sq'] / infl_df['influence_sq'].sum()
infl_df = infl_df.sort_values('influence_sq', ascending=False)
print()
print('='*78)
print('2. Per-cluster CR2-adjusted influence on the Satterthwaite df -- FULL 26-bank sample (AssetCostShare_raw, no branch_den)')
print(infl_df.head(10).to_string(index=False))
print(f"\nTotal df formula check: 2*(sum infl)^2 / sum(infl^2) = {2*(infl_df['influence'].sum()**2)/(infl_df['influence_sq'].sum()):.4f} (should match reported df=3.7885)")
print(f"TCB share of total influence^2: {infl_df.loc[infl_df['bank']=='TCB','share_of_total_sq'].values}")

# --- 3. Residual and leverage diagnostics for TCB specifically ---
print()
print('='*78)
print('3. TCB observation-level residuals and leverage (hat values)')
tcb_idx = np.where(groups == 'TCB')[0]
H_tcb = X[tcb_idx] @ inv @ X[tcb_idx].T
hat_diag = np.diag(H_tcb)
tcb_years = dprep.iloc[tcb_idx]['year'].values
tcb_resid = resid[tcb_idx]
tcb_zX = dprep.iloc[tcb_idx]['z_X'].values
print(pd.DataFrame({'year': tcb_years, 'z_X': tcb_zX, 'resid': tcb_resid, 'hat_diag': hat_diag}).to_string(index=False))
print(f"\nSum of TCB hat diagonal (own-cluster leverage): {hat_diag.sum():.4f}")
print(f"Mean hat diagonal across ALL observations: {np.diag(X @ inv @ X.T).mean():.4f}")

# --- 4. Re-run influence decomposition WITHOUT TCB (25-bank sample) to see who dominates after TCB leaves ---
d_no_tcb = dprep[dprep[idc].astype(str) != 'TCB'].copy()
X2, y2, resid2, beta2, inv2, cols2, groups2 = iv._fit(d_no_tcb, 'AssetCostShare_raw', xvars)
cov2 = iv._covariances(X2, resid2, inv2, groups2)
j2 = cols2.index('z_X')
contrast2 = np.zeros(len(cols2)); contrast2[j2] = 1
infl_notcb = {gkey: float(contrast2 @ inv2 @ q) for gkey, q in cov2['qg'].items()}
infl2_df = pd.DataFrame({'bank': list(infl_notcb.keys()), 'influence': list(infl_notcb.values())})
infl2_df['influence_sq'] = infl2_df['influence'] ** 2
infl2_df['share_of_total_sq'] = infl2_df['influence_sq'] / infl2_df['influence_sq'].sum()
infl2_df = infl2_df.sort_values('influence_sq', ascending=False)
print()
print('='*78)
print('4. Per-cluster influence AFTER removing TCB (25-bank sample) -- who now dominates?')
print(infl2_df.head(10).to_string(index=False))
df2 = 2*(infl2_df['influence'].sum()**2)/(infl2_df['influence_sq'].sum())
print(f"\ndf formula check (no-TCB): {df2:.4f} (should match reported df=2.3769)")

infl_df.to_csv(OUTDIR / 'tcb_influence_full_sample.csv', index=False)
infl2_df.to_csv(OUTDIR / 'tcb_influence_no_tcb_sample.csv', index=False)
print('\nSaved diagnostic CSVs to 10_era/')
