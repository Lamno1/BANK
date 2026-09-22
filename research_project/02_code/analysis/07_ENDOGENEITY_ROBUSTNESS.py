#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
07_ENDOGENEITY_ROBUSTNESS.py
Prioritized robustness / identification diagnostics for the final 26-bank panel.

A) Lead falsification (temporal placebo / anticipation-reverse-causality diagnostic)
   For CASA, SW_delta and SW_stock, estimate current X together with consecutive
   future X(t+1), X(t+2), then test H0: lead1 = lead2 = 0.
   Outcomes: CI, NonAssetMinusAsset, AssetCostShare, Staff/TA, ln(Network).

B) Bank-specific linear trends
   Re-estimate the same outcome battery after adding delta_i * t for each bank
   (one bank trend omitted as reference), alongside bank FE and year FE.

These checks strengthen or weaken particular alternative explanations but do NOT
by themselves establish causal identification.
"""
from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd

BASE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('b', BASE/'H1_H5_UNIFIED_HARMONIZED.py')
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

PANEL=BASE/'panel_master (1).csv'
NETWORK=BASE/'so phong chi nhanh.xlsx'
PREDICTORS=[('CASA','CASA','benchmark'),('SW_delta','Software Flow','supplementary'),('SW_stock','Software Stock','primary')]
ROWS=[]


def add(method,predictor,label,role,outcome,test,coef=np.nan,se=np.nan,stat=np.nan,p=np.nan,N=np.nan,G=np.nan,note=''):
    ROWS.append(dict(method=method,predictor=predictor,label=label,role=role,outcome=outcome,
                     test=test,coef=coef,se_CR2=se,statistic=stat,p_value=p,N=N,G=G,note=note))


def make_consecutive_future_leads(df,pred):
    D=df.sort_values(['Mã','year']).copy()
    for k in [1,2]:
        D[f'_year_lead{k}']=D.groupby('Mã')['year'].shift(-k)
        D[f'_x_lead{k}_raw']=D.groupby('Mã')[pred].shift(-k)
        ok=(pd.to_numeric(D[f'_year_lead{k}'],errors='coerce')-pd.to_numeric(D['year'],errors='coerce')==k).fillna(False)
        D[f'_x_lead{k}']=np.where(ok,D[f'_x_lead{k}_raw'],np.nan)
    return D


def _raw_outcome_frame(dr,dw):
    rawcols=['Mã','year','NonAssetMinusAsset_raw','AssetCostShare_raw','Staff_raw']
    D=dw.drop(columns=[c for c in rawcols[2:] if c in dw.columns],errors='ignore').merge(
        dr[rawcols],on=['Mã','year'],how='left',validate='one_to_one')
    D['lnNetwork']=np.where(D['network_count_harmonized']>0,np.log(D['network_count_harmonized']),np.nan)
    return D


def lead_falsification(dr,dw):
    source=_raw_outcome_frame(dr,dw)
    outcomes=[
        ('CI','CI','cost_intensity',True),
        ('NonAssetMinusAsset','NonAssetMinusAsset_raw','H4_absolute_contrast',True),
        ('AssetCostShare','AssetCostShare_raw','H4_composition',True),
        ('Staff/TA','Staff_raw','H4_staff',True),
        ('ln(Network)','lnNetwork','H4a_network',False),
    ]
    for pred,label,role in PREDICTORS:
        L=make_consecutive_future_leads(source,pred)
        for outlabel,yvar,note,include_branch in outcomes:
            req=[pred,'_x_lead1','_x_lead2',yvar]+b.CTRL+(['branch_den'] if include_branch else [])
            D=L.replace([np.inf,-np.inf],np.nan).dropna(subset=req).copy()
            # Standardize within the exact locked lead-test sample.
            D['z_X']=b.z(D[pred]); D['z_lead1']=b.z(D['_x_lead1']); D['z_lead2']=b.z(D['_x_lead2'])
            x=['z_X','z_lead1','z_lead2']
            if include_branch:
                D['z_Branch']=b.z(D['branch_den']); x.append('z_Branch')
            for c in b.CTRL: D['z_'+c]=b.z(D[c])
            x += ['z_'+c for c in b.CTRL]
            r=b.ols_cr2(D,yvar,x,return_full=True)
            for v,tname in [('z_X','current X'),('z_lead1','lead +1'),('z_lead2','lead +2')]:
                q=r[v]
                add('lead_falsification',pred,label,role,outlabel,tname,q['coef'],q['se'],q['t'],q['p'],r['_N'],r['_G'],note)
            w=b.wald_cr2_full(r,['z_lead1','z_lead2'])
            add('lead_falsification',pred,label,role,outlabel,'joint leads +1=+2=0',np.nan,np.nan,w['F'],w['p'],r['_N'],r['_G'],f'{note}; df=({w["df1"]},{w["df2"]})')


def add_bank_trends(D):
    D=D.copy()
    years=pd.to_numeric(D['year'],errors='coerce')
    # Centering changes only the bank-FE intercept parameterization, not the fitted model.
    D['_t']=years-years.min()
    banks=sorted(D['Mã'].astype(str).unique())
    reference=banks[0]
    terms=[]
    for bank in banks[1:]:
        safe=''.join(ch if ch.isalnum() else '_' for ch in bank)
        v=f'_trend_{safe}'
        D[v]=D['_t']*(D['Mã'].astype(str)==bank).astype(float)
        terms.append(v)
    return D,terms,reference


def _prep_native(source,pred,yvar,include_branch):
    req=[pred,yvar]+b.CTRL+(['branch_den'] if include_branch else [])
    D=source.replace([np.inf,-np.inf],np.nan).dropna(subset=req).copy()
    D['z_X']=b.z(D[pred]); x=['z_X']
    if include_branch:
        D['z_Branch']=b.z(D['branch_den']); x.append('z_Branch')
    for c in b.CTRL: D['z_'+c]=b.z(D[c])
    x += ['z_'+c for c in b.CTRL]
    return D,x


def bank_specific_trends(dr,dw):
    source=_raw_outcome_frame(dr,dw)
    outcomes=[
        ('CI','CI','cost_intensity',True),
        ('NonAssetMinusAsset','NonAssetMinusAsset_raw','H4_absolute_contrast',True),
        ('AssetCostShare','AssetCostShare_raw','H4_composition',True),
        ('Staff/TA','Staff_raw','H4_staff',True),
        ('ln(Network)','lnNetwork','H4a_network',False),
    ]
    for pred,label,role in PREDICTORS:
        for outlabel,yvar,note,include_branch in outcomes:
            D,x=_prep_native(source,pred,yvar,include_branch)
            base=b.ols_cr2(D,yvar,x,return_full=True)
            q0=base['z_X']
            add('bank_specific_trend',pred,label,role,outlabel,'baseline same sample',q0['coef'],q0['se'],q0['t'],q0['p'],base['_N'],base['_G'],note)

            T,terms,reference=add_bank_trends(D)
            tr=b.ols_cr2(T,yvar,x+terms,return_full=True)
            q=tr['z_X']
            add('bank_specific_trend',pred,label,role,outlabel,'with bank-specific trends',q['coef'],q['se'],q['t'],q['p'],tr['_N'],tr['_G'],f'{note}; reference={reference}; trend_terms={len(terms)}')
            change=q['coef']-q0['coef']
            pct=100*change/abs(q0['coef']) if q0['coef']!=0 else np.nan
            add('bank_specific_trend',pred,label,role,outlabel,'coef change % vs baseline',change,np.nan,pct,np.nan,tr['_N'],tr['_G'],note)


def main():
    dr,dw,_=b.build_analysis_data(PANEL,NETWORK)
    print(f'[FINAL PRIVATE PANEL] N={len(dw)}, G={dw.Mã.nunique()}, years={dw.year.min()}-{dw.year.max()}')
    lead_falsification(dr,dw)
    bank_specific_trends(dr,dw)
    out=pd.DataFrame(ROWS)
    out.to_csv(BASE/'ENDOGENEITY_ROBUSTNESS_RESULTS.csv',index=False)
    print('Saved',BASE/'ENDOGENEITY_ROBUSTNESS_RESULTS.csv')


if __name__=='__main__':
    main()
