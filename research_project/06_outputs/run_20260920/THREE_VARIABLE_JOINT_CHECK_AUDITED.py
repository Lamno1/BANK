#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd

BASE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('b', BASE/'H1_H5_UNIFIED_HARMONIZED.py')
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
P=['CASA','SW_delta','SW_stock']
ROWS=[]

def add(domain,test,outcome,var,q,res):
    ROWS.append(dict(domain=domain,test=test,outcome=outcome,variable=var,coef=q['coef'],se=q['se'],t=q['t'],p=q['p'],N=res['_N'],G=res['_G']))

def zprep(D, include_branch=True):
    D=D.copy()
    for p in P: D['z_'+p]=b.z(D[p])
    if include_branch: D['z_Branch']=b.z(D['branch_den'])
    for c in b.CTRL: D['z_'+c]=b.z(D[c])
    return D

def main():
    dr,dw,_=b.build_analysis_data(BASE/'panel_master (1).csv',BASE/'so phong chi nhanh.xlsx')
    req=P+['CI','branch_den','network_count_harmonized']+b.CTRL
    C=dw.replace([np.inf,-np.inf],np.nan).dropna(subset=req).copy()
    print('common sample',len(C),C.Mã.nunique(),int(C.year.min()),int(C.year.max()))
    print('\nBank counts:')
    print(C.groupby('Mã').size().to_string())
    print('\nPredictor correlations:')
    print(C[P].corr().to_string())
    # standardized predictor VIFs only, as diagnostic
    Z=np.column_stack([np.ones(len(C))]+[b.z(C[p]).to_numpy() for p in P])
    print('\nApprox predictor VIFs:')
    for j,p in enumerate(P, start=1):
        y=Z[:,j]; X=np.delete(Z,j,axis=1)
        bh=np.linalg.lstsq(X,y,rcond=None)[0]; e=y-X@bh
        r2=1-(e@e)/((y-y.mean())@(y-y.mean()))
        print(p,1/(1-r2))

    D=zprep(C)
    x=['z_'+p for p in P]+['z_Branch']+['z_'+c for c in b.CTRL]
    r=b.ols_cr2(D,'CI',x,return_full=True)
    print('\nJOINT BASELINE CI')
    for p in P:
        q=r['z_'+p]; print(p,q); add('Baseline','All 3 jointly','CI','z_'+p,q,r)

    D['Post']=(D.year>=2020).astype(int)
    intvars=[]
    for p in P:
        v=p+'xPost'; D[v]=D['z_'+p]*D['Post']; intvars.append(v)
    D['BranchxPost']=D['z_Branch']*D['Post']
    xt=['z_'+p for p in P]+['z_Branch']+intvars+['BranchxPost']+['z_'+c for c in b.CTRL]
    rt=b.ols_cr2(D,'CI',xt,return_full=True)
    print('\nJOINT TEMPORAL')
    for p,v in zip(P,intvars):
        q=rt[v]; print(v,q); add('Temporal','All 3 x Post2020','CI',v,q,rt)

    rawcols=['Mã','year','CI_raw','Staff_raw','AssetCost_raw','Other_raw','NonAsset_raw','NonAssetMinusAsset_raw','AssetCostShare_raw','NonAssetShare_raw']
    # Preserve the original joint-run scaling: standardize on the 240-row common sample,
    # then apply the raw-outcome complete-case restriction (H4 N may become 239).
    H0=zprep(C)
    H=H0.drop(columns=[c for c in rawcols[2:] if c in H0.columns],errors='ignore').merge(dr[rawcols],on=['Mã','year'],how='left',validate='one_to_one')
    reqh=P+['branch_den']+b.CTRL+rawcols[2:]
    H=H.replace([np.inf,-np.inf],np.nan).dropna(subset=reqh).copy()
    xh=['z_'+p for p in P]+['z_Branch']+['z_'+c for c in b.CTRL]
    print('\nJOINT H4')
    for y in ['NonAssetMinusAsset_raw','AssetCostShare_raw','Staff_raw','AssetCost_raw','Other_raw']:
        rr=b.ols_cr2(H,y,xh)
        print(y)
        for p in P:
            q=rr['z_'+p]; print(' ',p,q); add('H4 joint',y,y,'z_'+p,q,rr)

    N=C[C.network_count_harmonized>0].copy(); N['lnNetwork']=np.log(N.network_count_harmonized); N=zprep(N,include_branch=False)
    xn=['z_'+p for p in P]+['z_'+c for c in b.CTRL]
    rn=b.ols_cr2(N,'lnNetwork',xn)
    print('\nJOINT NETWORK ln count')
    for p in P:
        q=rn['z_'+p]; print(p,q); add('Physical network','All 3 jointly','lnNetwork','z_'+p,q,rn)

    S=zprep(C)
    thr=C.lnTA.median(); S['BIG']=(S.lnTA>thr).astype(int)
    iv=[]
    for p in P:
        v=p+'xBIG'; S[v]=S['z_'+p]*S['BIG']; iv.append(v)
    xs=['z_'+p for p in P]+['BIG']+iv+['z_Branch']+['z_'+c for c in b.CTRL]
    rs=b.ols_cr2(S,'CI',xs)
    print('\nJOINT SIZE BIG interactions')
    for p,v in zip(P,iv):
        q=rs[v]; print(v,q); add('Scale','All 3 x BIG','CI',v,q,rs)

    out=pd.DataFrame(ROWS); out.to_csv(BASE/'THREE_VARIABLE_JOINT_RESULTS_RERUN.csv',index=False)
    print('\nSaved',BASE/'THREE_VARIABLE_JOINT_RESULTS_RERUN.csv')

if __name__=='__main__': main()
