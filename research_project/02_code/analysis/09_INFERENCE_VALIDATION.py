"""Gate 0.4: inference validation for locked associational specifications.

This module does not change an outcome, RHS, sample rule, or estimand. It compares
covariance and small-cluster inference methods on the same bank/year FE models:
conventional, bank-clustered, HC1-style bank-clustered, the project's CR2, a
coefficient-specific Satterthwaite approximation, and bank-level wild bootstrap.
The bootstrap is a null-imposed Rademacher wild cluster bootstrap for the focal
coefficient. It is an inference cross-check, not a new estimator.
"""
from pathlib import Path
import importlib.util
import json
import numpy as np
import pandas as pd
from scipy import stats as st

BASE = Path(__file__).resolve().parent
LOCKED = BASE.parents[1] / '01_data' / 'locked_inputs'
PANEL = LOCKED / 'panel_master_FINAL.csv'
NETWORK = LOCKED / 'so_phong_chi_nhanh_FINAL.xlsx'
SEED = 20260920
BOOT = 999

spec_mod = importlib.util.spec_from_file_location('base_model', BASE / 'H1_H5_UNIFIED_HARMONIZED.py')
b = importlib.util.module_from_spec(spec_mod)
spec_mod.loader.exec_module(b)


def _prepare(dw, predictor, outcome, with_branch):
    req = [predictor, outcome] + b.CTRL + (['branch_den'] if with_branch else [])
    d = dw.replace([np.inf, -np.inf], np.nan).dropna(subset=req).copy()
    # Match the locked redesigned-model transformation: sample z-score of the
    # winsorized/raw predictor supplied by the relevant locked data object.
    d['z_X'] = b.z(d[predictor])
    x = ['z_X']
    if with_branch:
        d['z_Branch'] = b.z(d['branch_den'])
        x.append('z_Branch')
    for c in b.CTRL:
        d['z_' + c] = b.z(d[c])
        x.append('z_' + c)
    return d, x


def _fit(d, yvar, xvars):
    idc = d.columns[0]
    parts = [pd.Series(1.0, index=d.index, name='const'), d[xvars],
             pd.get_dummies(d[idc], drop_first=True, dtype=float, prefix='bank'),
             pd.get_dummies(d['year'], drop_first=True, dtype=float, prefix='year')]
    design = pd.concat(parts, axis=1)
    X = design.to_numpy(float)
    y = d[yvar].to_numpy(float)
    cols = list(design.columns)
    groups = d[idc].astype(str).to_numpy()
    inv = np.linalg.pinv(X.T @ X)
    beta = inv @ X.T @ y
    resid = y - X @ beta
    return X, y, resid, beta, inv, cols, groups


def _covariances(X, resid, inv, groups):
    n, k = X.shape
    uniq = np.unique(groups)
    meat_cluster = np.zeros((k, k))
    meat_cr2 = np.zeros((k, k))
    qg = {}
    for g in uniq:
        idx = np.where(groups == g)[0]
        Xg, ug = X[idx], resid[idx]
        sg = Xg.T @ ug
        meat_cluster += np.outer(sg, sg)
        H = Xg @ inv @ Xg.T
        ev, evec = np.linalg.eigh(np.eye(len(idx)) - H)
        ev = np.clip(ev, 1e-8, None)
        A = evec @ np.diag(ev ** -0.5) @ evec.T
        q = Xg.T @ (A @ ug)
        qg[g] = q
        meat_cr2 += np.outer(q, q)
    V_ols = inv * (resid @ resid) / max(n - k, 1)
    V_cl = inv @ meat_cluster @ inv
    # HC1-style small-sample cluster adjustment.
    G = len(uniq)
    V_hc1 = V_cl * (G / max(G - 1, 1)) * ((n - 1) / max(n - k, 1))
    V_cr2 = inv @ meat_cr2 @ inv
    return {'conventional': V_ols, 'cluster': V_cl, 'cluster_hc1': V_hc1,
            'cr2': V_cr2, 'qg': qg, 'G': G, 'n': n, 'k': k}


def _satterthwaite(V, inv, qg, contrast):
    # For a scalar contrast, df = 2*(sum_g v_g)^2 / sum_g v_g^2,
    # where v_g is the squared CR2-adjusted cluster influence on the contrast.
    vals = []
    for q in qg.values():
        influence = float(contrast @ inv @ q)
        vals.append(influence ** 2)
    total = float(contrast @ V @ contrast)
    denom = float(np.sum(np.square(vals)))
    df = 2 * total * total / denom if denom > 0 else np.nan
    return float(df)


def _p_interval(beta, se, df):
    t = beta / se if se > 0 else np.nan
    p = 2 * st.t.sf(abs(t), df=df) if np.isfinite(t) else np.nan
    q = st.t.ppf(.975, df=df) if np.isfinite(df) and df > 0 else np.nan
    return t, p, beta - q * se, beta + q * se


def _wild_bootstrap(X, y, beta, inv, cols, groups, focal, B=BOOT, seed=SEED):
    """Null-imposed Rademacher wild cluster bootstrap for one coefficient."""
    j = cols.index(focal)
    R = np.zeros(len(cols)); R[j] = 1.0
    # Restricted fitted values under beta_focal = 0, retaining all nuisance RHS/FE.
    keep = np.ones(len(cols), dtype=bool); keep[j] = False
    X0 = X[:, keep]
    b0 = np.linalg.pinv(X0.T @ X0) @ X0.T @ y
    fitted0 = X0 @ b0
    u0 = y - fitted0
    uniq = np.unique(groups)
    rng = np.random.default_rng(seed)
    obs = float(R @ beta)
    draws = np.empty(B)
    for z in range(B):
        signs = {g: (1.0 if rng.integers(0, 2) else -1.0) for g in uniq}
        yb = fitted0 + np.array([u0[i] * signs[groups[i]] for i in range(len(y))])
        bb = inv @ X.T @ yb
        draws[z] = bb[j]
    p = (1 + np.sum(np.abs(draws) >= abs(obs))) / (B + 1)
    # This is a null-imposed bootstrap test. The bootstrap quantiles are not a
    # confidence interval for beta, so leave CI fields unavailable rather than
    # presenting the null distribution as an interval estimate.
    return float(p), np.nan, np.nan, B


def run_one(dw, predictor, outcome, label, with_branch):
    d, xvars = _prepare(dw, predictor, outcome, with_branch)
    X, y, resid, beta, inv, cols, groups = _fit(d, outcome, xvars)
    cov = _covariances(X, resid, inv, groups)
    j = cols.index('z_X'); contrast = np.zeros(len(cols)); contrast[j] = 1
    rows = []
    for method in ['conventional', 'cluster', 'cluster_hc1', 'cr2']:
        V = cov[method]; se = float(np.sqrt(max(V[j, j], 0)))
        df = cov['G'] - 1 if method != 'cr2' else _satterthwaite(V, inv, cov['qg'], contrast)
        t, p, lo, hi = _p_interval(beta[j], se, df)
        rows.append({'specification': label, 'predictor': predictor, 'outcome': outcome,
                     'with_branch_den': with_branch, 'method': method, 'coef': float(beta[j]),
                     'se': se, 'df': df, 't': t, 'p_value': p, 'ci_low': lo, 'ci_high': hi,
                     'N': cov['n'], 'G': cov['G'], 'K': cov['k'], 'bootstrap_reps': np.nan})
    p, lo, hi, reps = _wild_bootstrap(X, y, beta, inv, cols, groups, 'z_X')
    rows.append({'specification': label, 'predictor': predictor, 'outcome': outcome,
                 'with_branch_den': with_branch, 'method': 'wild_cluster_rademacher_null',
                 'coef': float(beta[j]), 'se': np.nan, 'df': np.nan, 't': np.nan,
                 'p_value': p, 'ci_low': lo, 'ci_high': hi, 'N': cov['n'], 'G': cov['G'],
                 'K': cov['k'], 'bootstrap_reps': reps})
    return rows, {'d': d, 'X': X, 'y': y, 'resid': resid, 'groups': groups, 'beta': beta,
                  'cols': cols, 'cov': cov, 'focal_index': j}


def cross_sectional_residual_diagnostic(fits):
    rows = []
    for label, fit in fits.items():
        d = fit['d'].copy(); d['_e'] = fit['resid'];
        wide = d.pivot(index='year', columns=d.columns[0], values='_e')
        corr = wide.corr(min_periods=4).to_numpy()
        tri = corr[np.triu_indices_from(corr, 1)]
        rows.append({'specification': label, 'years_used': int(wide.shape[0]),
                     'banks_with_residuals': int(wide.shape[1]),
                     'mean_pairwise_residual_corr': float(np.nanmean(tri)) if len(tri) else np.nan,
                     'median_pairwise_residual_corr': float(np.nanmedian(tri)) if len(tri) else np.nan,
                     'note': 'Descriptive residual dependence diagnostic; year FE do not prove cross-sectional independence.'})
    return rows


def main():
    dr, dw, thresholds = b.build_analysis_data(PANEL, NETWORK)
    idc = dr.columns[0]
    if dw.columns[0] != idc:
        dw = dw.rename(columns={dw.columns[0]: idc})
    comp = dw if 'AssetCostShare_raw' in dw.columns else dw.merge(
        dr[[idc, 'year', 'AssetCostShare_raw']],
        on=[idc, 'year'], how='left', validate='one_to_one')
    specs = [
        ('PRIMARY_stock_CI_without_network', 'SW_stock', 'CI', False),
        ('PRIMARY_stock_AssetCostShare_without_network', 'SW_stock', 'AssetCostShare_raw', False),
        ('SECONDARY_delta_CI_without_network', 'SW_delta', 'CI', False),
        ('SECONDARY_stock_CI_with_network', 'SW_stock', 'CI', True),
        ('SECONDARY_stock_AssetCostShare_with_network', 'SW_stock', 'AssetCostShare_raw', True),
        ('SECONDARY_delta_AssetCostShare_without_network', 'SW_delta', 'AssetCostShare_raw', False),
    ]
    # Use raw composition outcome created by build_analysis_data; the association
    # design otherwise follows the locked winsorized panel and control definitions.
    results, fits = [], {}
    for label, pred, outcome, branch in specs:
        rr, fit = run_one(comp if outcome == 'AssetCostShare_raw' else dw,
                          pred, outcome, label, branch)
        results.extend(rr); fits[label] = fit
    out = pd.DataFrame(results)
    out.to_csv(BASE / 'INFERENCE_VALIDATION_RESULTS.csv', index=False)
    cs = pd.DataFrame(cross_sectional_residual_diagnostic(fits))
    cs.to_csv(BASE / 'INFERENCE_CROSS_SECTIONAL_DIAGNOSTIC.csv', index=False)
    meta = {'seed': SEED, 'wild_bootstrap_replications': BOOT,
            'specifications': [s[0] for s in specs],
            'note': 'Same locked RHS/LHS/sample rules; inference comparison only.'}
    (BASE / 'INFERENCE_VALIDATION_METADATA.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(out[['specification','method','coef','se','df','p_value','ci_low','ci_high','N','G']].to_string(index=False))
    print('\nSaved INFERENCE_VALIDATION_RESULTS.csv and INFERENCE_CROSS_SECTIONAL_DIAGNOSTIC.csv')


if __name__ == '__main__':
    main()
