#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Symmetric re-evaluation of three focal variables on the same test battery.
Variables in panel: CASA, SW_delta (software net change), SW_stock (accumulated software value/capital).
Runs native usable sample and a three-variable common-sample sensitivity.
"""
from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd

BASE=Path(__file__).resolve().parent
SRC=BASE/'H1_H5_UNIFIED_HARMONIZED.py'
spec=importlib.util.spec_from_file_location('basepipe', SRC)
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

PREDICTORS=[
    ('CASA','CASA','Franchise / transactional deposit structure'),
    ('SW_delta','Software net change','Current-period net change in gross software value'),
    ('SW_stock','Software stock','Accumulated software value / digital capital'),
]
ROWS=[]

def rec(sample_mode,pred,label,domain,test,outcome,q,res,note=''):
    ROWS.append(dict(sample_mode=sample_mode,predictor=pred,label=label,domain=domain,test=test,
                     outcome=outcome,coef=q.get('coef',np.nan),se_CR2=q.get('se',np.nan),
                     t=q.get('t',np.nan),p_CR2=q.get('p',np.nan),N=res.get('_N',np.nan),G=res.get('_G',np.nan),note=note))

def prep(df,pred,extra_required=None,branch=True):
    req=[pred,'CI']+b.CTRL
    if branch: req+=['branch_den']
    if extra_required: req+=list(extra_required)
    D=df.replace([np.inf,-np.inf],np.nan).dropna(subset=list(dict.fromkeys(req))).copy()
    D['z_X']=b.z(D[pred])
    x=['z_X']
    if branch:
        D['z_Branch']=b.z(D['branch_den']); x+=['z_Branch']
    for c in b.CTRL: D['z_'+c]=b.z(D[c])
    x += ['z_'+c for c in b.CTRL]
    return D,x

def run_battery(dr,dw,sample_mode='native',common_keys=None):
    dwr=dw.copy(); drr=dr.copy()
    if common_keys is not None:
        keydf=pd.DataFrame(list(common_keys),columns=['Mã','year'])
        dwr=dwr.merge(keydf,on=['Mã','year'],how='inner',validate='one_to_one')
        drr=drr.merge(keydf,on=['Mã','year'],how='inner',validate='one_to_one')

    # Common size definitions are fixed within each sample_mode, not predictor-specific.
    BIG_THRESHOLD=dwr['lnTA'].median()
    bm=dwr.groupby('Mã')['lnTA'].mean(); fm_thr=bm.median(); fm_map=(bm>fm_thr).astype(int).to_dict()
    b15=dwr.loc[dwr.year==2015,['Mã','lnTA']].dropna().set_index('Mã')['lnTA']
    f15_thr=b15.median() if len(b15) else np.nan; f15_map=(b15>f15_thr).astype(int).to_dict() if len(b15) else {}

    rawcols=['Mã','year','CI_raw','Staff_raw','AssetCost_raw','Other_raw','NonAsset_raw',
             'NonAssetMinusAsset_raw','AssetCostShare_raw','NonAssetShare_raw']

    for pred,label,construct in PREDICTORS:
        print('\n'+'='*100); print(f'[{sample_mode}] {label} ({pred})'); print('='*100)

        # A. Baseline CI
        D,x=prep(dwr,pred)
        r=b.ols_cr2(D,'CI',x,return_full=True); q=r['z_X']
        rec(sample_mode,pred,label,'Baseline','CI baseline','CI',q,r,construct)
        print(f'Baseline CI: beta={q["coef"]:+.6f}, p={q["p"]:.5f}, N={r["_N"]}, G={r["_G"]}')

        # B. Temporal shift Post-2020 (symmetric)
        D['Post']=(D['year']>=2020).astype(int)
        D['XxPost']=D['z_X']*D['Post']; D['BranchxPost']=D['z_Branch']*D['Post']
        xt=['z_X','z_Branch','XxPost','BranchxPost']+['z_'+c for c in b.CTRL]
        rt=b.ols_cr2(D,'CI',xt,return_full=True); qt=rt['XxPost']
        rec(sample_mode,pred,label,'Temporal','X × Post2020','CI',qt,rt)
        spre=b.lincom_cr2(rt,{'z_X':1.0}); spost=b.lincom_cr2(rt,{'z_X':1.0,'XxPost':1.0})
        rec(sample_mode,pred,label,'Temporal','Pre-2020 slope','CI',spre,rt)
        rec(sample_mode,pred,label,'Temporal','Post-2020 slope','CI',spost,rt)
        print(f'Temporal XxPost: beta={qt["coef"]:+.6f}, p={qt["p"]:.5f}; pre p={spre["p"]:.5f}; post p={spost["p"]:.5f}')

        # C. H4 cost reconfiguration (same model for all three)
        DD=dwr.drop(columns=[c for c in rawcols[2:] if c in dwr.columns],errors='ignore').merge(
            drr[rawcols],on=['Mã','year'],how='left',validate='one_to_one')
        req=[pred,'branch_den']+b.CTRL+rawcols[2:]
        DD=DD.replace([np.inf,-np.inf],np.nan).dropna(subset=req).copy()
        DD['z_X']=b.z(DD[pred]); DD['z_Branch']=b.z(DD['branch_den'])
        for c in b.CTRL: DD['z_'+c]=b.z(DD[c])
        xh=['z_X','z_Branch']+['z_'+c for c in b.CTRL]
        outs=['CI_raw','Staff_raw','AssetCost_raw','Other_raw','NonAsset_raw','NonAssetMinusAsset_raw','AssetCostShare_raw','NonAssetShare_raw']
        rr={y:b.ols_cr2(DD,y,xh) for y in outs}
        ng={(rr[y]['_N'],rr[y]['_G']) for y in outs}; assert len(ng)==1
        bci=rr['CI_raw']['z_X']['coef']; bs=rr['Staff_raw']['z_X']['coef']; ba=rr['AssetCost_raw']['z_X']['coef']; bo=rr['Other_raw']['z_X']['coef']
        bna=rr['NonAsset_raw']['z_X']['coef']; bd=rr['NonAssetMinusAsset_raw']['z_X']['coef']
        assert abs(bci-(bs+ba+bo))<1e-12
        assert abs(bd-(bna-ba))<1e-12
        assert abs(rr['AssetCostShare_raw']['z_X']['coef']+rr['NonAssetShare_raw']['z_X']['coef'])<1e-12
        for test,y in [('H4 absolute contrast','NonAssetMinusAsset_raw'),('H4 direct composition share','AssetCostShare_raw'),('H4 Staff component','Staff_raw'),('H4 AssetCost component','AssetCost_raw'),('H4 Other component','Other_raw')]:
            rec(sample_mode,pred,label,'Cost reconfiguration',test,y,rr[y]['z_X'],rr[y])
        print(f'H4 contrast p={rr["NonAssetMinusAsset_raw"]["z_X"]["p"]:.5f}; AssetShare p={rr["AssetCostShare_raw"]["z_X"]["p"]:.5f}; Staff p={rr["Staff_raw"]["z_X"]["p"]:.5f}')

        # D. Physical network, primary ln count + secondary intensity; no branch RHS
        DN=dwr.replace([np.inf,-np.inf],np.nan).dropna(subset=[pred,'network_count_harmonized','ta']+b.CTRL).copy()
        DN=DN[DN.network_count_harmonized>0].copy()
        DN['lnNetwork']=np.log(DN.network_count_harmonized)
        DN['NetworkIntensity']=DN.network_count_harmonized/(DN.ta/1e14)
        DN['z_X']=b.z(DN[pred])
        for c in b.CTRL: DN['z_'+c]=b.z(DN[c])
        xn=['z_X']+['z_'+c for c in b.CTRL]
        rn=b.ols_cr2(DN,'lnNetwork',xn); qn=rn['z_X']; rec(sample_mode,pred,label,'Physical network','ln(network count)','lnNetwork',qn,rn)
        ri=b.ols_cr2(DN,'NetworkIntensity',xn); qi=ri['z_X']; rec(sample_mode,pred,label,'Physical network','network/TA intensity','NetworkIntensity',qi,ri)
        print(f'Network ln count: beta={qn["coef"]:+.6f}, p={qn["p"]:.5f}; intensity p={qi["p"]:.5f}')

        # E. Size moderation, same four definitions
        D,x=prep(dwr,pred)
        D['BIG']=(D.lnTA>BIG_THRESHOLD).astype(int); D['XxBIG']=D['z_X']*D['BIG']
        x5=['z_X','BIG','XxBIG','z_Branch']+['z_'+c for c in b.CTRL]
        r5=b.ols_cr2(D,'CI',x5,return_full=True); q5=r5['XxBIG']; rec(sample_mode,pred,label,'Scale','BIG bank-year interaction','CI',q5,r5)
        small=b.lincom_cr2(r5,{'z_X':1}); large=b.lincom_cr2(r5,{'z_X':1,'XxBIG':1})
        rec(sample_mode,pred,label,'Scale','Small-bank slope','CI',small,r5); rec(sample_mode,pred,label,'Scale','Large-bank slope','CI',large,r5)
        D['BIGfm']=D['Mã'].map(fm_map); D['XxBIGfm']=D['z_X']*D['BIGfm']
        rf=b.ols_cr2(D,'CI',['z_X','XxBIGfm','z_Branch']+['z_'+c for c in b.CTRL]); rec(sample_mode,pred,label,'Scale','BIG fixed mean','CI',rf['XxBIGfm'],rf)
        D['BIG15']=D['Mã'].map(f15_map); D['XxBIG15']=D['z_X']*D['BIG15']; d15=D.dropna(subset=['BIG15'])
        if len(d15):
            r15=b.ols_cr2(d15,'CI',['z_X','XxBIG15','z_Branch']+['z_'+c for c in b.CTRL]); rec(sample_mode,pred,label,'Scale','BIG fixed 2015','CI',r15['XxBIG15'],r15)
            p15=r15['XxBIG15']['p']
        else: p15=np.nan
        D['XxlnTA']=D['z_X']*D['z_lnTA']
        rc=b.ols_cr2(D,'CI',['z_X','XxlnTA','z_Branch']+['z_'+c for c in b.CTRL]); rec(sample_mode,pred,label,'Scale','Continuous lnTA interaction','CI',rc['XxlnTA'],rc)
        print(f'Scale: BIG p={q5["p"]:.5f}; fixed mean p={rf["XxBIGfm"]["p"]:.5f}; 2015 p={p15:.5f}; continuous p={rc["XxlnTA"]["p"]:.5f}')


def main():
    dr,dw,_=b.build_analysis_data(BASE/'panel_master (1).csv',BASE/'so phong chi nhanh.xlsx')
    run_battery(dr,dw,'native',None)
    req=['CASA','SW_delta','SW_stock','CI','branch_den','network_count_harmonized']+b.CTRL
    c=dw.replace([np.inf,-np.inf],np.nan).dropna(subset=req)[['Mã','year']]
    common_keys=set(map(tuple,c[['Mã','year']].itertuples(index=False,name=None)))
    print(f'\n[COMMON SAMPLE] bank-years={len(common_keys)}, banks={c.Mã.nunique()}, years={c.year.min()}-{c.year.max()}')
    run_battery(dr,dw,'common3',common_keys)
    out=pd.DataFrame(ROWS)
    out.to_csv(BASE/'THREE_VARIABLE_SYMMETRIC_RESULTS.csv',index=False)
    print('\nSaved',BASE/'THREE_VARIABLE_SYMMETRIC_RESULTS.csv')

if __name__=='__main__': main()
