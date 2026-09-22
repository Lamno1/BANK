"""Gate 0.5A: complete preferred inference for remaining canonical hypotheses.

The canonical specifications are reconstructed from H1_H5_UNIFIED_HARMONIZED.py.
Only covariance/inference is changed: no outcome, RHS, interaction, sample rule,
or estimand is redesigned here.
"""
from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
LOCKED = BASE.parents[1] / '01_data' / 'locked_inputs'
PANEL = LOCKED / 'panel_master_FINAL.csv'
NETWORK = LOCKED / 'so_phong_chi_nhanh_FINAL.xlsx'

def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

b = load('base_model', BASE / 'H1_H5_UNIFIED_HARMONIZED.py')
iv = load('inference_validation', BASE / '09_INFERENCE_VALIDATION.py')


def infer(d, outcome, xvars, focal, label, role):
    X, y, resid, beta, inv, cols, groups = iv._fit(d, outcome, xvars)
    cov = iv._covariances(X, resid, inv, groups)
    j = cols.index(focal); contrast = np.zeros(len(cols)); contrast[j] = 1
    rows=[]
    for method in ['conventional','cluster','cluster_hc1','cr2']:
        V=cov[method]; se=float(np.sqrt(max(V[j,j],0)))
        df=cov['G']-1 if method!='cr2' else iv._satterthwaite(V,inv,cov['qg'],contrast)
        t,p,lo,hi=iv._p_interval(beta[j],se,df)
        rows.append({'hypothesis':label,'role':role,'outcome':outcome,'focal':focal,
                     'method':method,'coef':float(beta[j]),'se':se,'df':df,'t':t,
                     'p_value':p,'ci_low':lo,'ci_high':hi,'N':cov['n'],'G':cov['G']})
    p,lo,hi,reps=iv._wild_bootstrap(X,y,beta,inv,cols,groups,focal)
    rows.append({'hypothesis':label,'role':role,'outcome':outcome,'focal':focal,
                 'method':'wild_cluster_rademacher_null','coef':float(beta[j]),'se':np.nan,
                 'df':np.nan,'t':np.nan,'p_value':p,'ci_low':np.nan,'ci_high':np.nan,
                 'N':cov['n'],'G':cov['G']})
    return rows


def prep_raw_h4(dr,dw,digcol):
    idc=dw.columns[0]
    raw=['CI_raw','Staff_raw','AssetCost_raw','Other_raw','NonAsset_raw',
         'NonAssetMinusAsset_raw','AssetCostShare_raw','NonAssetShare_raw']
    D=dw.drop(columns=[c for c in raw if c in dw.columns],errors='ignore').merge(
        dr[[idc,'year']+raw],on=[idc,'year'],how='left',validate='one_to_one')
    req=[digcol,'branch_den']+b.CTRL+raw
    D=D.replace([np.inf,-np.inf],np.nan).dropna(subset=req).copy()
    D['FI_dig']=b.mm(D[digcol]); D['z_FI_dig']=b.z(D['FI_dig'])
    D['FI_trad']=b.mm(D['branch_den']); D['z_FI_trad']=b.z(D['FI_trad'])
    for c in b.CTRL: D['z_'+c]=b.z(D[c])
    return D


def main():
    dr,dw,_=b.build_analysis_data(PANEL,NETWORK)
    if dr.columns[0] != dw.columns[0]: dw=dw.rename(columns={dw.columns[0]:dr.columns[0]})
    rows=[]

    # H1 and H2 canonical baseline/temporal models: prep_fi includes branch_den.
    D,x=b.prep_fi(dw,'CASA'); rows += infer(D,'CI',x,'z_FI_dig','H1 CASA baseline','benchmark')
    D,x=b.prep_fi(dw,'SW_delta'); rows += infer(D,'CI',x,'z_FI_dig','H2 Flow baseline','primary_temporal')
    D=D.copy(); D['Post']=(D['year']>=2020).astype(int)
    D['digxpost']=D['z_FI_dig']*D['Post']; D['tradxpost']=D['z_FI_trad']*D['Post']
    xt=['z_FI_dig','z_FI_trad','digxpost','tradxpost']+['z_'+c for c in b.CTRL]
    rows += infer(D,'CI',xt,'digxpost','H2 Flow x Post2020','primary_temporal')

    # H4a canonical network-as-outcome models: no branch_den on RHS.
    for digcol,role in [('SW_stock','primary_supplementary'),('SW_delta','secondary_supplementary')]:
        D=dw.replace([np.inf,-np.inf],np.nan).dropna(subset=[digcol,'network_count_harmonized']+b.CTRL).copy()
        D=D[D['network_count_harmonized']>0].copy(); D['lnNetworkCount_raw']=np.log(D['network_count_harmonized'])
        D['FI_dig']=b.mm(D[digcol]); D['z_FI_dig']=b.z(D['FI_dig'])
        for c in b.CTRL: D['z_'+c]=b.z(D[c])
        xn=['z_FI_dig']+['z_'+c for c in b.CTRL]
        rows += infer(D,'lnNetworkCount_raw',xn,'z_FI_dig',f'H4a {digcol} -> ln network',role)

    # H5 canonical interactions, including the two stated robustness variants.
    BIG_THRESHOLD=dw['lnTA'].median(); idc=dw.columns[0]
    bank_mean=dw.groupby(idc)['lnTA'].mean(); fixed_mean_thr=bank_mean.median(); fixed_mean=(bank_mean>fixed_mean_thr).astype(int).to_dict()
    base15=dw.loc[dw['year']==2015,[idc,'lnTA']].dropna().set_index(idc)['lnTA']; fixed15=(base15>base15.median()).astype(int).to_dict()
    for digcol,role in [('SW_stock','primary_boundary'),('SW_delta','secondary_boundary'),('CASA','benchmark_boundary')]:
        D,x=b.prep_fi(dw,digcol); D=D.copy(); D['BIG']=(D['lnTA']>BIG_THRESHOLD).astype(int); D['DxBIG']=D['z_FI_dig']*D['BIG']
        x5=['z_FI_dig','BIG','DxBIG','z_FI_trad']+['z_'+c for c in b.CTRL]
        rows += infer(D,'CI',x5,'DxBIG',f'H5 {digcol} x BIG_it',role)
        D['BIG_fixed_mean']=D[idc].map(fixed_mean); D['DxBIGfm']=D['z_FI_dig']*D['BIG_fixed_mean']
        rows += infer(D,'CI',['z_FI_dig','DxBIGfm','z_FI_trad']+['z_'+c for c in b.CTRL],'DxBIGfm',f'H5 {digcol} x BIG_fixed_mean','robustness')
        D['BIG_fixed_2015']=D[idc].map(fixed15); D15=D.dropna(subset=['BIG_fixed_2015']).copy(); D15['DxBIGf15']=D15['z_FI_dig']*D15['BIG_fixed_2015']
        rows += infer(D15,'CI',['z_FI_dig','DxBIGf15','z_FI_trad']+['z_'+c for c in b.CTRL],'DxBIGf15',f'H5 {digcol} x BIG_2015','robustness')
        D['FIxlnTA']=D['z_FI_dig']*D['z_lnTA']
        rows += infer(D,'CI',['z_FI_dig','FIxlnTA','z_FI_trad']+['z_'+c for c in b.CTRL],'FIxlnTA',f'H5 {digcol} x continuous lnTA','robustness')

    out=pd.DataFrame(rows); out.to_csv(BASE/'REMAINING_HYPOTHESIS_INFERENCE.csv',index=False)
    print(out[out.method.isin(['cr2','wild_cluster_rademacher_null'])][['hypothesis','method','coef','df','p_value','N','G']].to_string(index=False))
    print('Saved REMAINING_HYPOTHESIS_INFERENCE.csv')

if __name__=='__main__': main()
