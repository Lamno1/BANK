#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06_MODEL_DIAGNOSTICS.py
Diagnostics for the final three-variable panel architecture.

Inputs:
  panel_master (1).csv
  so phong chi nhanh.xlsx
  H1_H5_UNIFIED_HARMONIZED.py

Diagnostics:
  A) Serial correlation: Wooldridge/Drukker-style first-difference test + FE residual AR(1) check.
  B) Multicollinearity: two-way-FE residualized correlations and VIF, native models + joint common sample.
  C) Endogeneity diagnostic for SW_delta: lagged-value control function with locked first-stage sample.
  D) Exclusion warning: distributed-lag CR2 model and joint Wald test for lag1=lag2=0.

These are diagnostics, not new primary hypothesis tests.
"""
from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd
from scipy import stats as st
import statsmodels.api as sm

BASE = Path(__file__).resolve().parent
SRC = BASE / 'H1_H5_UNIFIED_HARMONIZED.py'
spec = importlib.util.spec_from_file_location('basepipe', SRC)
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

PANEL = BASE / 'panel_master (1).csv'
NETWORK = BASE / 'so phong chi nhanh.xlsx'
FOCALS = [('CASA','CASA'), ('SW_delta','Software net change'), ('SW_stock','Software stock')]
ROWS=[]

def add(section, predictor, test, statistic=np.nan, p=np.nan, N=np.nan, G=np.nan, note=''):
    ROWS.append(dict(section=section,predictor=predictor,test=test,statistic=statistic,p_value=p,N=N,G=G,note=note))


def _baseline_sample(dw, pred):
    req=[pred,'CI','branch_den']+b.CTRL
    D=dw.replace([np.inf,-np.inf],np.nan).dropna(subset=req).copy().sort_values(['Mã','year'])
    D['z_X']=b.z(D[pred]); D['z_Branch']=b.z(D['branch_den'])
    for c in b.CTRL: D['z_'+c]=b.z(D[c])
    x=['z_X','z_Branch']+['z_'+c for c in b.CTRL]
    return D,x


def _residualize_two_way(D, cols):
    # Residualize each continuous regressor on bank and year FE (plus intercept).
    FE=pd.concat([
        pd.Series(1.0,index=D.index,name='const'),
        pd.get_dummies(D['Mã'],drop_first=True,dtype=float,prefix='bank'),
        pd.get_dummies(D['year'],drop_first=True,dtype=float,prefix='year')
    ],axis=1).to_numpy(float)
    P=np.linalg.pinv(FE.T@FE)@FE.T
    out=pd.DataFrame(index=D.index)
    for c in cols:
        y=D[c].to_numpy(float)
        out[c]=y-FE@(P@y)
    return out


def _vif_table(X):
    rows=[]
    A=X.to_numpy(float)
    for j,c in enumerate(X.columns):
        y=A[:,j]
        idx=[k for k in range(A.shape[1]) if k!=j]
        if not idx:
            vif=1.0
        else:
            Z=np.column_stack([np.ones(len(y)),A[:,idx]])
            beta=np.linalg.pinv(Z.T@Z)@Z.T@y
            resid=y-Z@beta
            sst=((y-y.mean())**2).sum(); ssr=(resid**2).sum()
            R2=1-ssr/sst if sst>0 else np.nan
            vif=np.inf if np.isfinite(R2) and R2>=1-1e-12 else 1/(1-R2) if np.isfinite(R2) else np.nan
        rows.append((c,vif))
    return pd.DataFrame(rows,columns=['variable','VIF'])


def wooldridge_fd_test(D, pred):
    """Wooldridge/Drukker-style diagnostic.
    1) First-difference y and continuous regressors for consecutive bank-years.
    2) Regress dy on dx + year dummies, obtain FD residual u.
    3) Regress u_t on u_{t-1} (no constant), cluster by bank, test H0 rho=-0.5.
    Under no serial correlation in level errors, FD errors have rho approximately -0.5.
    """
    D=D.sort_values(['Mã','year']).copy()
    # baseline standardized regressors already prepared
    xcols=['z_X','z_Branch']+['z_'+c for c in b.CTRL]
    for c in ['CI']+xcols:
        D['d_'+c]=D.groupby('Mã')[c].diff()
    D['year_l1']=D.groupby('Mã')['year'].shift(1)
    fd=D[(D['year']-D['year_l1']==1)].dropna(subset=['d_CI']+['d_'+c for c in xcols]).copy()
    if len(fd)==0: return np.nan,np.nan,0,0,np.nan
    # year dummies represent differenced common year effects
    parts=[fd[['d_'+c for c in xcols]].astype(float),pd.get_dummies(fd['year'],drop_first=True,dtype=float,prefix='year')]
    X=pd.concat(parts,axis=1).to_numpy(float)
    y=fd['d_CI'].to_numpy(float)
    # no intercept in differenced equation; year dummies absorb time shifts
    bh=np.linalg.pinv(X.T@X)@X.T@y
    fd['u_fd']=y-X@bh
    fd['u_lag']=fd.groupby('Mã')['u_fd'].shift(1)
    fd['yr_lag']=fd.groupby('Mã')['year'].shift(1)
    ar=fd[(fd['year']-fd['yr_lag']==1)].dropna(subset=['u_lag']).copy()
    if len(ar)<5: return np.nan,np.nan,len(ar),ar['Mã'].nunique(),np.nan
    # u = rho u_lag, no constant. Cluster-robust conventional sandwich, small-sample corrected.
    model=sm.OLS(ar['u_fd'].to_numpy(float), ar[['u_lag']].to_numpy(float)).fit(
        cov_type='cluster', cov_kwds={'groups':ar['Mã'].astype(str).to_numpy(),'use_correction':True}
    )
    rho=float(model.params[0]); se=float(model.bse[0]); G=ar['Mã'].nunique()
    t=(rho+0.5)/se
    p=2*st.t.sf(abs(t),df=max(G-1,1))
    return rho,p,len(ar),G,se


def fe_residual_ar1(D,x):
    full=b.ols_cr2(D,'CI',x,return_full=True)
    s=D.loc[full['_sample_index']].copy(); s['e']=full['_resid']
    s=s.sort_values(['Mã','year'])
    s['e_lag']=s.groupby('Mã')['e'].shift(1); s['yr_lag']=s.groupby('Mã')['year'].shift(1)
    a=s[(s.year-s.yr_lag==1)].dropna(subset=['e_lag']).copy()
    if len(a)<5: return np.nan,np.nan,len(a),a['Mã'].nunique(),np.nan
    m=sm.OLS(a['e'].to_numpy(float), sm.add_constant(a[['e_lag']].to_numpy(float))).fit(
        cov_type='cluster', cov_kwds={'groups':a['Mã'].astype(str).to_numpy(),'use_correction':True}
    )
    rho=float(m.params[1]); se=float(m.bse[1]); G=a['Mã'].nunique(); t=rho/se
    p=2*st.t.sf(abs(t),df=max(G-1,1))
    return rho,p,len(a),G,se


def run_serial(dw):
    print('\n'+'='*100+'\nA. SERIAL CORRELATION DIAGNOSTICS\n'+'='*100)
    for pred,label in FOCALS:
        D,x=_baseline_sample(dw,pred)
        rho,p,N,G,se=wooldridge_fd_test(D,pred)
        print(f'{label:<24} Wooldridge-style rho_FD={rho:+.4f}, H0 rho=-0.5, p={p:.5f}, N={N}, G={G}')
        add('serial_correlation',pred,'Wooldridge-style FD H0 rho=-0.5',rho,p,N,G,f'se={se:.6g}')
        r2,p2,N2,G2,se2=fe_residual_ar1(D,x)
        print(f'{"":24} FE residual AR(1) rho={r2:+.4f}, H0 rho=0, p={p2:.5f}, N={N2}, G={G2}')
        add('serial_correlation',pred,'FE residual AR1 H0 rho=0',r2,p2,N2,G2,f'se={se2:.6g}')


def run_vif(dw):
    print('\n'+'='*100+'\nB. MULTICOLLINEARITY (TWO-WAY-FE RESIDUALIZED VIF)\n'+'='*100)
    # Native models
    for pred,label in FOCALS:
        D,x=_baseline_sample(dw,pred)
        W=_residualize_two_way(D,x)
        vt=_vif_table(W)
        print(f'\n{label} native sample: N={len(D)}, G={D.Mã.nunique()}')
        print(vt.to_string(index=False,formatters={'VIF':'{:.3f}'.format}))
        for _,r in vt.iterrows(): add('multicollinearity',pred,f'native VIF {r.variable}',r.VIF,np.nan,len(D),D.Mã.nunique(),'two-way-FE residualized')
    # Joint common sample
    req=['CASA','SW_delta','SW_stock','CI','branch_den']+b.CTRL
    D=dw.replace([np.inf,-np.inf],np.nan).dropna(subset=req).copy()
    for p,_ in FOCALS: D['z_'+p]=b.z(D[p])
    D['z_Branch']=b.z(D.branch_den)
    for c in b.CTRL: D['z_'+c]=b.z(D[c])
    cols=['z_CASA','z_SW_delta','z_SW_stock','z_Branch']+['z_'+c for c in b.CTRL]
    W=_residualize_two_way(D,cols)
    vt=_vif_table(W)
    corr=W[['z_CASA','z_SW_delta','z_SW_stock']].corr()
    print(f'\nJOINT common sample: N={len(D)}, G={D.Mã.nunique()}')
    print('Within-FE focal correlation:')
    print(corr.round(3).to_string())
    print('\nWithin-FE full VIF:')
    print(vt.to_string(index=False,formatters={'VIF':'{:.3f}'.format}))
    for _,r in vt.iterrows(): add('multicollinearity','joint3',f'joint VIF {r.variable}',r.VIF,np.nan,len(D),D.Mã.nunique(),'two-way-FE residualized')
    for i in corr.index:
        for j in corr.columns:
            if i<j: add('multicollinearity','joint3',f'within-FE corr {i} vs {j}',corr.loc[i,j],np.nan,len(D),D.Mã.nunique())


def make_consecutive_lags(dw):
    D=dw.sort_values(['Mã','year']).copy()
    for k in [1,2]:
        D[f'year_lag{k}']=D.groupby('Mã')['year'].shift(k)
        D[f'SW_lag{k}_raw']=D.groupby('Mã')['SW_delta'].shift(k)
        ok=(pd.to_numeric(D['year'],errors='coerce')-pd.to_numeric(D[f'year_lag{k}'],errors='coerce')==k).fillna(False).to_numpy(bool)
        D[f'SW_lag{k}']=np.where(ok,D[f'SW_lag{k}_raw'],np.nan)
    return D


def run_endogeneity(dw):
    print('\n'+'='*100+'\nC. ENDOGENEITY / CONTROL-FUNCTION DIAGNOSTIC FOR SW_delta\n'+'='*100)
    D=make_consecutive_lags(dw)
    req=['SW_delta','CI','branch_den']+b.CTRL
    D=D.replace([np.inf,-np.inf],np.nan).dropna(subset=req).copy()
    D['z_SW']=b.z(D.SW_delta); D['z_Branch']=b.z(D.branch_den)
    for c in b.CTRL: D['z_'+c]=b.z(D[c])
    CT=['z_'+c for c in b.CTRL]

    sub=D.dropna(subset=['SW_lag1']).copy()
    sub['z_SW_lag1']=b.z(sub.SW_lag1)
    first_x=['z_SW_lag1','z_Branch']+CT
    # Lock exact first-stage sample before deriving residuals.
    locked=b.estimation_sample(sub,'z_SW',first_x,min_cluster_obs=3)
    first=b.ols_cr2(locked,'z_SW',first_x,min_cluster_obs=0,return_full=True)
    assert first['_N']==len(locked) and first['_G']==locked.Mã.nunique()
    locked=locked.copy(); locked['v_hat']=first['_resid'].reindex(locked.index)
    fs=first['z_SW_lag1']
    print(f'First-stage lag1: coef={fs["coef"]:+.6f}, CR2 t={fs["t"]:.3f}, p={fs["p"]:.8f}, N={first["_N"]}, G={first["_G"]}')
    add('endogeneity','SW_delta','first-stage lag1 relevance',fs['coef'],fs['p'],first['_N'],first['_G'],f't={fs["t"]:.4f}')

    second_x=['z_SW','v_hat','z_Branch']+CT
    haus=b.ols_cr2(locked,'CI',second_x,min_cluster_obs=0,return_full=True)
    vh=haus['v_hat']
    print(f'Residual inclusion v_hat: coef={vh["coef"]:+.6f}, CR2 t={vh["t"]:.3f}, p={vh["p"]:.8f}, N={haus["_N"]}, G={haus["_G"]}')
    add('endogeneity','SW_delta','control-function residual inclusion',vh['coef'],vh['p'],haus['_N'],haus['_G'],f't={vh["t"]:.4f}')

    print('\nD. DISTRIBUTED LAG / EXCLUSION-RESTRICTION WARNING')
    sub2=D.dropna(subset=['SW_lag1','SW_lag2']).copy()
    for c in ['SW_delta','SW_lag1','SW_lag2']: sub2['z_'+c]=b.z(sub2[c])
    xdl=['z_SW_delta','z_SW_lag1','z_SW_lag2','z_Branch']+CT
    dl=b.ols_cr2(sub2,'CI',xdl,return_full=True)
    for key in ['z_SW_delta','z_SW_lag1','z_SW_lag2']:
        q=dl[key]
        print(f'{key:<14} coef={q["coef"]:+.6f}, p={q["p"]:.6f}')
        add('distributed_lag','SW_delta',key,q['coef'],q['p'],dl['_N'],dl['_G'])
    w=b.wald_cr2_full(dl,['z_SW_lag1','z_SW_lag2'])
    print(f'Joint H0 lag1=lag2=0: F={w["F"]:.4f}, p={w["p"]:.8f}, df=({w["df1"]},{w["df2"]})')
    add('distributed_lag','SW_delta','joint lag1=lag2=0',w['F'],w['p'],dl['_N'],dl['_G'],f'df=({w["df1"]},{w["df2"]})')


def main():
    dr,dw,_=b.build_analysis_data(PANEL,NETWORK)
    print(f'[PRIVATE PANEL] N={len(dw)}, G={dw.Mã.nunique()}, years={dw.year.min()}-{dw.year.max()}')
    run_serial(dw)
    run_vif(dw)
    run_endogeneity(dw)
    out=pd.DataFrame(ROWS)
    out.to_csv(BASE/'MODEL_DIAGNOSTICS_RESULTS.csv',index=False)
    print('\nSaved',BASE/'MODEL_DIAGNOSTICS_RESULTS.csv')

if __name__=='__main__': main()
