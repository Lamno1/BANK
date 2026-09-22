#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H1-H5 UNIFIED PIPELINE — harmonized physical-network version
Inputs (same folder by default):
  1) panel_master.csv
  2) so phong chi nhanh.xlsx  [harmonized physical service-point counts]

Research architecture implemented here
--------------------------------------
H1  Franchise capability: CASA -> CI.
H2  Current-period software accumulation: SW_delta -> CI, plus temporal shift after 2020.
H3  Accumulated digital capital: SW_stock -> CI.
H4  Structural reconfiguration:
      H4R-A    absolute contrast: (NonAsset/TA - AssetCost/TA) ~ SW_stock
      H4R-COMP direct composition: AssetCost/OPEX ~ SW_stock
      H4a      physical network: ln(harmonized network count) ~ SW_stock
    SW_delta versions are supplementary, not the primary H4 tests.
H5  Scale boundary condition: SW_stock x BIG(bank-year) -> CI.
    Fixed-bank classifications and continuous lnTA interaction are robustness checks.

Inference protocol
------------------
- Bank FE + year FE.
- CR2 covariance (Bell-McCaffrey leverage adjustment).
- Individual coefficients / linear contrasts: t reference with df=G-1.
- Joint Wald tests: F(q,G-1).
- Winsorization thresholds computed ONCE on the full private-bank panel (SOE==0).
- Accounting decomposition outcomes are RAW ratios, never independently winsorized.
- Harmonized branch/network data REPLACE legacy branch_count/branch_den for analysis.

This is an associational panel design. Coefficients should not be described as causal effects
without additional identification assumptions/designs.
"""
from pathlib import Path
import argparse
import re
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from scipy import stats as st

BASE_DIR = Path(__file__).resolve().parent
CTRL = ['lnTA','eq_ratio','loan_ratio','NPL_ratio','dep_depth']

# -----------------------------------------------------------------------------
# Core helpers
# -----------------------------------------------------------------------------
def z(s):
    sd = s.std()
    if not np.isfinite(sd) or sd == 0:
        raise ValueError(f"Cannot z-score {getattr(s, 'name', '<unknown>')}: sd={sd}")
    return (s - s.mean()) / sd


def mm(s):
    rng = s.max() - s.min()
    if not np.isfinite(rng) or rng == 0:
        raise ValueError(f"Cannot min-max {getattr(s, 'name', '<unknown>')}: range={rng}")
    return (s - s.min()) / rng


def star(p):
    return '***' if p < .01 else '**' if p < .05 else '*' if p < .10 else ''


def estimation_sample(df, yvar, xvars, year_fe=True, min_cluster_obs=3):
    req = [yvar] + list(xvars) + ['Mã'] + (['year'] if year_fe else [])
    out = df.dropna(subset=list(dict.fromkeys(req))).copy()
    if min_cluster_obs:
        vc = out['Mã'].value_counts()
        keep = vc[vc >= min_cluster_obs].index
        out = out[out['Mã'].isin(keep)].copy()
    return out


def _design_matrix(df, xvars, year_fe=True):
    parts = [
        pd.Series(1.0, index=df.index, name='const'),
        df[xvars],
        pd.get_dummies(df['Mã'], drop_first=True, dtype=float, prefix='bank')
    ]
    if year_fe:
        parts.append(pd.get_dummies(df['year'], drop_first=True, dtype=float, prefix='year'))
    return pd.concat(parts, axis=1)


def ols_cr2(df, yvar, xvars, year_fe=True, min_cluster_obs=3, return_full=False):
    d = estimation_sample(df, yvar, xvars, year_fe=year_fe, min_cluster_obs=min_cluster_obs)
    if len(d) == 0:
        raise ValueError(f"Empty estimation sample: {yvar} ~ {xvars}")
    X = _design_matrix(d, xvars, year_fe=year_fe)
    Xn = X.to_numpy(float)
    y = d[yvar].to_numpy(float)
    XtX_inv = np.linalg.pinv(Xn.T @ Xn)
    beta = XtX_inv @ Xn.T @ y
    resid = y - Xn @ beta

    meat = np.zeros((Xn.shape[1], Xn.shape[1]))
    groups = d['Mã'].astype(str).to_numpy()
    for g in np.unique(groups):
        idx = np.where(groups == g)[0]
        Xg, ug = Xn[idx], resid[idx]
        Hgg = Xg @ XtX_inv @ Xg.T
        I_H = np.eye(len(idx)) - Hgg
        ev, evec = np.linalg.eigh(I_H)
        ev = np.clip(ev, 1e-8, None)
        A = evec @ np.diag(ev ** -0.5) @ evec.T
        sc = Xg.T @ (A @ ug)
        meat += np.outer(sc, sc)

    V = XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(V), 0.0))
    G = d['Mã'].nunique()
    if G < 2:
        raise ValueError('Need at least 2 bank clusters.')

    cols = list(X.columns)
    out = {}
    for xv in xvars:
        i = cols.index(xv)
        t = beta[i] / se[i] if se[i] > 0 else np.nan
        p = 2 * st.t.sf(abs(t), df=G-1) if np.isfinite(t) else np.nan
        out[xv] = {'coef': float(beta[i]), 'se': float(se[i]), 't': float(t),
                   'p': float(p), 'df': int(G-1)}
    out['_N'] = int(len(d)); out['_G'] = int(G); out['_df_ref'] = int(G-1)
    if return_full:
        out['_beta'] = beta; out['_V'] = V; out['_cols'] = cols
        out['_sample_index'] = d.index.copy(); out['_resid'] = pd.Series(resid, index=d.index)
    return out


def lincom_cr2(full, weights):
    beta, V, cols, G = full['_beta'], full['_V'], full['_cols'], full['_G']
    a = np.zeros(len(cols))
    for var, w in weights.items():
        if var not in cols:
            raise KeyError(f'{var} absent from full specification')
        a[cols.index(var)] = w
    est = float(a @ beta)
    var = float(a @ V @ a)
    se = np.sqrt(max(var, 0.0))
    t = est / se if se > 0 else np.nan
    p = 2 * st.t.sf(abs(t), df=G-1) if np.isfinite(t) else np.nan
    return {'coef': est, 'se': float(se), 't': float(t), 'p': float(p), 'df': int(G-1)}


def wald_cr2_full(full, restrict_vars):
    beta, V, cols, G = full['_beta'], full['_V'], full['_cols'], full['_G']
    q = len(restrict_vars)
    R = np.zeros((q, len(cols)))
    for j, v in enumerate(restrict_vars):
        if v not in cols:
            raise KeyError(f'{v} absent from full specification')
        R[j, cols.index(v)] = 1
    Rb = R @ beta; RVR = R @ V @ R.T
    W = float(Rb.T @ np.linalg.pinv(RVR) @ Rb)
    F = W / q
    p = st.f.sf(F, q, G-1)
    return {'F': float(F), 'p': float(p), 'df1': int(q), 'df2': int(G-1)}


def winsorize_lock(df, cols, lo=.01, hi=.99):
    out = df.copy(); thresholds = {}
    for c in cols:
        if c in out.columns and out[c].notna().sum() > 10:
            lv, hv = out[c].quantile(lo), out[c].quantile(hi)
            thresholds[c] = (float(lv), float(hv))
            out[c] = out[c].clip(lv, hv)
    return out, thresholds


# -----------------------------------------------------------------------------
# Harmonized network loader
# -----------------------------------------------------------------------------
def load_harmonized_network(xlsx_path):
    xlsx_path = Path(xlsx_path)
    if not xlsx_path.exists():
        raise FileNotFoundError(xlsx_path)
    xls = pd.ExcelFile(xlsx_path)
    target = None; df = None
    for sh in xls.sheet_names:
        tmp = pd.read_excel(xlsx_path, sheet_name=sh)
        cols = [str(c) for c in tmp.columns]
        if 'Mã' in tmp.columns and any(('Số lượng chi nhánh năm' in c or 'chi nhánh năm' in c.lower()) for c in cols):
            target = sh; df = tmp; break
    if df is None:
        raise ValueError('Could not find harmonized branch/network sheet.')

    year_cols = []
    for c in df.columns:
        m = re.search(r'(20\d{2})', str(c))
        if m and ('chi nhánh' in str(c).lower() or 'điểm giao dịch' in str(c).lower()):
            year_cols.append((c, int(m.group(1))))
    if not year_cols:
        raise ValueError('No year-specific branch/network columns found.')

    pieces = []
    for c, yr in year_cols:
        p = df[['Mã', c]].copy()
        p.columns = ['Mã', 'network_count_harmonized']
        p['year'] = yr
        pieces.append(p)
    net = pd.concat(pieces, ignore_index=True)
    net['Mã'] = net['Mã'].astype(str).str.strip()
    net['network_count_harmonized'] = pd.to_numeric(net['network_count_harmonized'], errors='coerce')
    net = net.dropna(subset=['Mã','year','network_count_harmonized']).copy()
    net = net[net['network_count_harmonized'] > 0].copy()
    dup = net.duplicated(['Mã','year'], keep=False)
    if dup.any():
        raise ValueError(f'Duplicate bank-year network rows: {net.loc[dup,["Mã","year"]].head().to_dict("records")}')
    print(f'[NETWORK] sheet="{target}"; valid bank-years={len(net)}; banks={net["Mã"].nunique()}; years={net.year.min()}-{net.year.max()}')
    return net


# -----------------------------------------------------------------------------
# Data build: replace old branch measure with harmonized network count
# -----------------------------------------------------------------------------
def build_analysis_data(panel_path, network_path):
    panel_path = Path(panel_path)
    if not panel_path.exists():
        raise FileNotFoundError(
            f'Missing real research panel: {panel_path}. This script will NOT substitute synthetic data.'
        )
    d = pd.read_csv(panel_path)
    required = ['Mã','year','SOE','ta','opex','staff','phys','CI','CASA','SW_stock','SW_delta'] + CTRL
    miss = [c for c in required if c not in d.columns]
    if miss:
        raise KeyError(f'panel_master.csv missing required columns: {miss}')
    d = d[d['SOE'] == 0].copy()
    d['Mã'] = d['Mã'].astype(str).str.strip()
    d['year'] = pd.to_numeric(d['year'], errors='coerce').astype('Int64')

    net = load_harmonized_network(network_path)
    if 'branch_count' in d.columns:
        d = d.rename(columns={'branch_count':'branch_count_legacy'})
    if 'branch_den' in d.columns:
        d = d.rename(columns={'branch_den':'branch_den_legacy'})
    d = d.merge(net, on=['Mã','year'], how='left', validate='one_to_one')
    matched = d['network_count_harmonized'].notna().sum()
    print(f'[NETWORK MERGE] private panel N={len(d)}; matched={matched} ({matched/len(d):.1%}); missing={len(d)-matched}')
    if matched == 0:
        raise ValueError('No bank-year matches between panel and harmonized network file.')

    # Rebuild the branch variable used throughout the hypothesis system.
    d['branch_count'] = d['network_count_harmonized']
    d['branch_den'] = d['network_count_harmonized'] / (d['ta'] / 1e14)

    # RAW accounting decomposition; never separately winsorized.
    d['CI_raw'] = d['opex'] / d['ta']
    d['Staff_raw'] = d['staff'].abs() / d['ta']
    d['AssetCost_raw'] = d['phys'].abs() / d['ta']
    d['Other_raw'] = d['CI_raw'] - d['Staff_raw'] - d['AssetCost_raw']
    d['NonAsset_raw'] = d['Staff_raw'] + d['Other_raw']
    d['NonAssetMinusAsset_raw'] = d['NonAsset_raw'] - d['AssetCost_raw']

    valid_ci = np.isfinite(d['CI_raw']) & (d['CI_raw'] > 0)
    d['AssetCostShare_raw'] = np.nan
    d['NonAssetShare_raw'] = np.nan
    d.loc[valid_ci, 'AssetCostShare_raw'] = d.loc[valid_ci, 'AssetCost_raw'] / d.loc[valid_ci, 'CI_raw']
    d.loc[valid_ci, 'NonAssetShare_raw'] = d.loc[valid_ci, 'NonAsset_raw'] / d.loc[valid_ci, 'CI_raw']

    # Observation-level hard identities.
    g = (d['CI_raw'] - (d['Staff_raw'] + d['AssetCost_raw'] + d['Other_raw'])).abs().dropna()
    if len(g): assert g.max() < 1e-12, f'Accounting identity failed at observation level: {g.max()}'
    sg = (d['AssetCostShare_raw'] + d['NonAssetShare_raw'] - 1).abs().dropna()
    if len(sg): assert sg.max() < 1e-12, f'Cost-share identity failed: {sg.max()}'

    # Locked winsorization on full private panel AFTER harmonized branch replacement.
    winsor_cols = ['CI','CASA','SW_stock','SW_delta','branch_den','lnTA','eq_ratio',
                   'loan_ratio','NPL_ratio','dep_depth','PhysCost','StaffRatio','cost_dep',
                   'Land_stock','Land_delta']
    dw, thresholds = winsorize_lock(d, winsor_cols)
    return d, dw, thresholds


# -----------------------------------------------------------------------------
# Result collector
# -----------------------------------------------------------------------------
ROWS = []
def record(hyp, test, construct, outcome, variable, q, res, role='PRIMARY', note=''):
    ROWS.append({
        'hypothesis': hyp, 'test': test, 'role': role, 'construct': construct,
        'outcome': outcome, 'variable': variable,
        'coef': q.get('coef', np.nan), 'se_CR2': q.get('se', np.nan),
        't': q.get('t', np.nan), 'p_CR2': q.get('p', np.nan),
        'N': res.get('_N', np.nan), 'G': res.get('_G', np.nan), 'note': note
    })


def prep_fi(dw, digcol, required_outcomes=('CI',), include_branch=True):
    req = [digcol] + list(required_outcomes) + CTRL + (['branch_den'] if include_branch else [])
    D = dw.replace([np.inf,-np.inf], np.nan).dropna(subset=req).copy()
    D['FI_dig'] = mm(D[digcol]); D['z_FI_dig'] = z(D['FI_dig'])
    x = ['z_FI_dig']
    if include_branch:
        D['FI_trad'] = mm(D['branch_den']); D['z_FI_trad'] = z(D['FI_trad']); x.append('z_FI_trad')
    for c in CTRL: D['z_'+c] = z(D[c])
    x += ['z_'+c for c in CTRL]
    return D, x


# -----------------------------------------------------------------------------
# H1-H5
# -----------------------------------------------------------------------------
def run_all_hypotheses(dr, dw):
    print('\n' + '='*110)
    print('H1 — FRANCHISE CAPABILITY: CASA -> CI')
    print('='*110)
    D, x = prep_fi(dw, 'CASA')
    c = ols_cr2(D, 'CI', x)
    q = c['z_FI_dig']; record('H1','CASA baseline','Franchise capability','CI','z_CASA',q,c)
    print(f'H1 CASA: coef={q["coef"]:+.6f}, p={q["p"]:.5f}{star(q["p"])}; N={c["_N"]}, G={c["_G"]}')

    print('\n' + '='*110)
    print('H2 — SOFTWARE NET CHANGE: current-period accumulation + temporal shift')
    print('='*110)
    D, x = prep_fi(dw, 'SW_delta')
    c = ols_cr2(D, 'CI', x)
    q = c['z_FI_dig']; record('H2','Net-change baseline','Software net change','CI','z_SW_delta',q,c)
    print(f'H2 baseline: coef={q["coef"]:+.6f}, p={q["p"]:.5f}{star(q["p"])}')
    D['Post'] = (D['year'] >= 2020).astype(int)
    D['digxpost'] = D['z_FI_dig'] * D['Post']
    D['tradxpost'] = D['z_FI_trad'] * D['Post']
    xt = ['z_FI_dig','z_FI_trad','digxpost','tradxpost'] + ['z_'+c for c in CTRL]
    c2 = ols_cr2(D,'CI',xt,return_full=True)
    q2 = c2['digxpost']; record('H2','Post-2020 interaction','Software net change','CI','SW_delta x Post2020',q2,c2,role='PRIMARY-TEMPORAL')
    w = wald_cr2_full(c2,['digxpost','tradxpost'])
    print(f'H2 SW_delta x Post2020: coef={q2["coef"]:+.6f}, p={q2["p"]:.5f}{star(q2["p"])}; joint Wald p={w["p"]:.5f}')

    print('\n' + '='*110)
    print('H3 — ACCUMULATED DIGITAL CAPITAL: Software Stock -> CI')
    print('='*110)
    D, x = prep_fi(dw, 'SW_stock')
    c3 = ols_cr2(D,'CI',x)
    q3 = c3['z_FI_dig']; record('H3','Stock baseline','Accumulated digital capital','CI','z_SW_stock',q3,c3)
    print(f'H3 SW_stock: coef={q3["coef"]:+.6f}, p={q3["p"]:.5f}{star(q3["p"])}; N={c3["_N"]}, G={c3["_G"]}')

    print('\n' + '='*110)
    print('H4 — STRUCTURAL RECONFIGURATION')
    print('='*110)
    for digcol, name, role in [('SW_stock','Software Stock','PRIMARY'),('SW_delta','Software net change','SUPPLEMENTARY')]:
        # use winsorized FI/branch/controls but RAW accounting outcomes from dr
        rawcols = ['Mã','year','CI_raw','Staff_raw','AssetCost_raw','Other_raw','NonAsset_raw',
                   'NonAssetMinusAsset_raw','AssetCostShare_raw','NonAssetShare_raw']
        D = dw.drop(columns=[c for c in rawcols[2:] if c in dw.columns], errors='ignore').merge(
            dr[rawcols], on=['Mã','year'], how='left', validate='one_to_one')
        req = [digcol,'branch_den'] + CTRL + rawcols[2:]
        D = D.replace([np.inf,-np.inf],np.nan).dropna(subset=req).copy()
        D['FI_dig']=mm(D[digcol]); D['z_FI_dig']=z(D['FI_dig'])
        D['FI_trad']=mm(D['branch_den']); D['z_FI_trad']=z(D['FI_trad'])
        for cc in CTRL: D['z_'+cc]=z(D[cc])
        xh=['z_FI_dig','z_FI_trad']+['z_'+cc for cc in CTRL]
        outs=['CI_raw','Staff_raw','AssetCost_raw','Other_raw','NonAsset_raw','NonAssetMinusAsset_raw','AssetCostShare_raw','NonAssetShare_raw']
        res={y:ols_cr2(D,y,xh) for y in outs}
        ng={(res[y]['_N'],res[y]['_G']) for y in outs}; assert len(ng)==1, f'H4 samples differ: {ng}'
        bci=res['CI_raw']['z_FI_dig']['coef']; bs=res['Staff_raw']['z_FI_dig']['coef']; ba=res['AssetCost_raw']['z_FI_dig']['coef']; bo=res['Other_raw']['z_FI_dig']['coef']
        bna=res['NonAsset_raw']['z_FI_dig']['coef']; bd=res['NonAssetMinusAsset_raw']['z_FI_dig']['coef']
        assert abs(bci-(bs+ba+bo))<1e-12
        assert abs(bd-(bna-ba))<1e-12
        bas=res['AssetCostShare_raw']['z_FI_dig']['coef']; bnas=res['NonAssetShare_raw']['z_FI_dig']['coef']
        assert abs(bas+bnas)<1e-12
        qa=res['NonAssetMinusAsset_raw']['z_FI_dig']
        qc=res['AssetCostShare_raw']['z_FI_dig']
        qs=res['Staff_raw']['z_FI_dig']
        record('H4','H4R-A absolute contrast',name,'NonAsset/TA - AssetCost/TA','z_'+digcol,qa,res['NonAssetMinusAsset_raw'],role=role,
               note='Valid absolute intensity contrast; not by itself a pure composition test.')
        record('H4','H4R-COMP direct share',name,'AssetCost/OPEX','z_'+digcol,qc,res['AssetCostShare_raw'],role=role,
               note='Direct cost-composition test; NonAsset share coefficient is exact negative.')
        record('H4','Staff component',name,'StaffCost/TA','z_'+digcol,qs,res['Staff_raw'],role='COMPONENT-'+role)
        print(f'{name}: H4R-A delta={qa["coef"]:+.6f}, p={qa["p"]:.5f}{star(qa["p"])} | H4R-COMP AssetShare beta={qc["coef"]:+.6f}, p={qc["p"]:.5f}{star(qc["p"])} | Staff p={qs["p"]:.5f}')

        # H4a: direct harmonized physical-network stock, no branch control.
        Dn = dw.replace([np.inf,-np.inf],np.nan).dropna(subset=[digcol,'network_count_harmonized']+CTRL).copy()
        Dn = Dn[Dn['network_count_harmonized']>0].copy()
        Dn['lnNetworkCount_raw']=np.log(Dn['network_count_harmonized'])
        Dn['NetworkIntensity_per100trn_raw']=Dn['network_count_harmonized']/(Dn['ta']/1e14)
        Dn['FI_dig']=mm(Dn[digcol]); Dn['z_FI_dig']=z(Dn['FI_dig'])
        for cc in CTRL: Dn['z_'+cc]=z(Dn[cc])
        xn=['z_FI_dig']+['z_'+cc for cc in CTRL]
        cn=ols_cr2(Dn,'lnNetworkCount_raw',xn)
        qn=cn['z_FI_dig']
        record('H4a','Physical network primary',name,'ln(harmonized network count)','z_'+digcol,qn,cn,role=role)
        ci=ols_cr2(Dn,'NetworkIntensity_per100trn_raw',xn)
        qi=ci['z_FI_dig']
        record('H4a','Physical network intensity',name,'network count per 1e14 TA','z_'+digcol,qi,ci,role='SECONDARY-'+role)
        print(f'{name}: H4a ln(network) coef={qn["coef"]:+.6f}, p={qn["p"]:.5f}{star(qn["p"])} | intensity p={qi["p"]:.5f}')

    print('\n' + '='*110)
    print('H5 — SCALE BOUNDARY CONDITION: Software Stock x Size')
    print('='*110)
    BIG_THRESHOLD = dw['lnTA'].median()
    bank_mean_full = dw.groupby('Mã')['lnTA'].mean(); fixed_mean_thr = bank_mean_full.median()
    fixed_mean_map = (bank_mean_full > fixed_mean_thr).astype(int).to_dict()
    base2015 = dw.loc[dw['year']==2015,['Mã','lnTA']].dropna().set_index('Mã')['lnTA']
    fixed_2015_thr = base2015.median(); fixed_2015_map=(base2015>fixed_2015_thr).astype(int).to_dict()

    for digcol,name,role in [('SW_stock','Software Stock','PRIMARY'),('SW_delta','Software net change','SUPPLEMENTARY'),('CASA','CASA franchise comparator','COMPARATOR')]:
        D,x = prep_fi(dw,digcol)
        D['BIG']=(D['lnTA']>BIG_THRESHOLD).astype(int)
        D['DxBIG']=D['z_FI_dig']*D['BIG']
        x5=['z_FI_dig','BIG','DxBIG','z_FI_trad']+['z_'+cc for cc in CTRL]
        c5=ols_cr2(D,'CI',x5,return_full=True)
        q5=c5['DxBIG']; record('H5','BIG bank-year interaction',name,'CI',f'{digcol} x BIG_it',q5,c5,role=role)
        small=lincom_cr2(c5,{'z_FI_dig':1.0}); large=lincom_cr2(c5,{'z_FI_dig':1.0,'DxBIG':1.0})
        print(f'{name}: MAIN DxBIG coef={q5["coef"]:+.6f}, p={q5["p"]:.5f}{star(q5["p"])} | slope small p={small["p"]:.5f}, large p={large["p"]:.5f}')

        D['BIG_fixed_mean']=D['Mã'].map(fixed_mean_map); D['DxBIGfm']=D['z_FI_dig']*D['BIG_fixed_mean']
        cb=ols_cr2(D,'CI',['z_FI_dig','DxBIGfm','z_FI_trad']+['z_'+cc for cc in CTRL])
        qb=cb['DxBIGfm']; record('H5','BIG fixed bank mean',name,'CI',f'{digcol} x BIG_fixed_mean',qb,cb,role='ROBUSTNESS')

        D['BIG_fixed_2015']=D['Mã'].map(fixed_2015_map); D['DxBIGf15']=D['z_FI_dig']*D['BIG_fixed_2015']
        d15=D.dropna(subset=['BIG_fixed_2015'])
        cc=ols_cr2(d15,'CI',['z_FI_dig','DxBIGf15','z_FI_trad']+['z_'+v for v in CTRL])
        qc=cc['DxBIGf15']; record('H5','BIG fixed 2015',name,'CI',f'{digcol} x BIG_2015',qc,cc,role='ROBUSTNESS')

        D['FIxlnTA']=D['z_FI_dig']*D['z_lnTA']
        cd=ols_cr2(D,'CI',['z_FI_dig','FIxlnTA','z_FI_trad']+['z_'+v for v in CTRL])
        qd=cd['FIxlnTA']; record('H5','Continuous size interaction',name,'CI',f'{digcol} x z_lnTA',qd,cd,role='ROBUSTNESS')
        print(f'   robustness p: fixed-mean={qb["p"]:.5f}; fixed-2015={qc["p"]:.5f}; continuous={qd["p"]:.5f}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--panel', default=str(BASE_DIR/'panel_master.csv'))
    ap.add_argument('--network', default=str(BASE_DIR/'so phong chi nhanh.xlsx'))
    ap.add_argument('--out', default=str(BASE_DIR/'H1_H5_results_harmonized.csv'))
    ap.add_argument('--validate-network-only', action='store_true')
    args = ap.parse_args()

    if args.validate_network_only:
        net = load_harmonized_network(args.network)
        print(net.groupby('year')['network_count_harmonized'].count().to_string())
        return

    dr,dw,thresholds = build_analysis_data(args.panel,args.network)
    print(f'[WINSOR] locked thresholds for {len(thresholds)} variables on full private panel.')
    run_all_hypotheses(dr,dw)
    out = pd.DataFrame(ROWS)
    out.to_csv(args.out,index=False)
    print('\n'+'='*110)
    print(f'SAVED RESULT TABLE: {args.out}')
    print('='*110)
    print(out[['hypothesis','test','role','construct','outcome','coef','p_CR2','N','G']].to_string(index=False))


if __name__ == '__main__':
    main()
