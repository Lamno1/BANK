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

iv = load('iv_h4a_diag', ANALYSIS / '09_INFERENCE_VALIDATION.py')
b = iv.b
panel_path = BASE / '01_data' / 'locked_inputs' / 'panel_master_FINAL.csv'
network_path = BASE / '01_data' / 'locked_inputs' / 'so_phong_chi_nhanh_FINAL.xlsx'
dr, dw, thresholds = b.build_analysis_data(panel_path, network_path)
idc = dw.columns[0]

Dn = dw.replace([np.inf, -np.inf], np.nan).dropna(subset=['SW_stock', 'network_count_harmonized'] + b.CTRL).copy()
Dn = Dn[Dn['network_count_harmonized'] > 0].copy()
Dn['lnNetworkCount_raw'] = np.log(Dn['network_count_harmonized'])
Dn['FI_dig'] = b.mm(Dn['SW_stock']); Dn['z_FI_dig'] = b.z(Dn['FI_dig'])
for c in b.CTRL: Dn['z_' + c] = b.z(Dn[c])
xn = ['z_FI_dig'] + ['z_' + c for c in b.CTRL]

X, y, resid, beta, inv, cols, groups = iv._fit(Dn, 'lnNetworkCount_raw', xn)
j = cols.index('z_FI_dig')
obs = beta[j]

# --- Reimplement the wild bootstrap loop, but KEEP the draws and per-cluster null residuals ---
keep = np.ones(len(cols), dtype=bool); keep[j] = False
X0 = X[:, keep]
b0 = np.linalg.pinv(X0.T @ X0) @ X0.T @ y
fitted0 = X0 @ b0
u0 = y - fitted0
uniq = np.unique(groups)

# Per-cluster null-restricted residual sum of squares -- does one cluster dominate?
rss_by_cluster = {}
for g in uniq:
    idx = np.where(groups == g)[0]
    rss_by_cluster[g] = float(np.sum(u0[idx] ** 2))
rss_df = pd.DataFrame({'bank': list(rss_by_cluster.keys()), 'null_resid_ss': list(rss_by_cluster.values())})
rss_df['share'] = rss_df['null_resid_ss'] / rss_df['null_resid_ss'].sum()
rss_df = rss_df.sort_values('null_resid_ss', ascending=False)
print('Per-cluster null-restricted residual sum of squares (share of total):')
print(rss_df.head(8).to_string(index=False))

rng = np.random.default_rng(20260920)
B = 999
draws = np.empty(B)
for z in range(B):
    signs = {g: (1.0 if rng.integers(0, 2) else -1.0) for g in uniq}
    yb = fitted0 + np.array([u0[i] * signs[groups[i]] for i in range(len(y))])
    bb = inv @ X.T @ yb
    draws[z] = bb[j]

print()
print(f"Observed coefficient: {obs:.6f}")
print(f"Bootstrap draws: mean={draws.mean():.6f}, sd={draws.std():.6f}")
print(f"Bootstrap draws: min={draws.min():.6f}, max={draws.max():.6f}")

cov = iv._covariances(X, resid, inv, groups)
se_cr2 = float(np.sqrt(max(cov['cr2'][j, j], 0)))
print(f"CR2 SE = {se_cr2:.6f}   Bootstrap draws SD = {draws.std():.6f}   Ratio (bootstrap/CR2) = {draws.std()/se_cr2:.3f}")

p_boot = (1 + np.sum(np.abs(draws) >= abs(obs))) / (B + 1)
print(f"\nWild bootstrap p-value (reproduced): {p_boot:.6f}")
print(f"Share of |draws| exceeding |obs|={abs(obs):.6f}: {np.mean(np.abs(draws) >= abs(obs)):.4f}")

pct = (np.sum(draws <= obs)) / B * 100
print(f"Observed coefficient sits at the {pct:.1f}th percentile of the bootstrap draw distribution")

# --- Compare: what if we drop the single highest-RSS cluster from the bootstrap? ---
top_cluster = rss_df.iloc[0]['bank']
print(f"\nTop null-residual cluster: {top_cluster} (share={rss_df.iloc[0]['share']:.3f})")
idx_top = np.where(groups == top_cluster)[0]
print(f"z_FI_dig range for {top_cluster}: [{Dn.iloc[idx_top]['z_FI_dig'].min():.3f}, {Dn.iloc[idx_top]['z_FI_dig'].max():.3f}]")
print(f"lnNetworkCount_raw range for {top_cluster}: [{Dn.iloc[idx_top]['lnNetworkCount_raw'].min():.3f}, {Dn.iloc[idx_top]['lnNetworkCount_raw'].max():.3f}]")
print(f"Residual (unrestricted model) for {top_cluster}:")
print(resid[idx_top])

rss_df.to_csv(BASE / '10_era' / 'h4a_null_residual_by_cluster.csv', index=False)
pd.Series(draws).to_csv(BASE / '10_era' / 'h4a_wild_bootstrap_draws.csv', index=False)
print('\nSaved diagnostics to 10_era/')
