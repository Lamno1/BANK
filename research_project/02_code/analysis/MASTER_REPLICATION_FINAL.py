#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MASTER_REPLICATION_FINAL.py
Final single-entry replication pipeline for the 26-bank study.

Required source inputs in --workdir:
  panel_master_base.csv        financial panel before final software refresh
  SOURCE_FINAL_so_hoa.xlsx     locked final digitized source workbook

Code modules:
  00_BUILD_FINAL_INPUTS.py
  H1_H5_UNIFIED_HARMONIZED.py
  THREE_VARIABLE_SYMMETRIC_EVAL.py
  THREE_VARIABLE_JOINT_CHECK_AUDITED.py
  06_MODEL_DIAGNOSTICS.py
  07_ENDOGENEITY_ROBUSTNESS.py

Pipeline:
  0) rebuild SW_stock/SW_delta with source rule 0/1 -> NA and copy locked network source;
  1) audit final inputs and common-three sample;
  2) H1-H5 canonical models;
  3) symmetric native/common-three battery;
  4) joint CASA + Software Flow + Software Stock sensitivity;
  5) serial-correlation, VIF and control-function/distributed-lag diagnostics;
  6) prioritized lead falsification and bank-specific linear-trend robustness;
  7) SHA-256 reproducibility manifest.

Interpretation remains associational. No module in this pipeline turns the design into a
causal design without a defensible external/quasi-experimental source of exogenous variation.
"""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, importlib.util, json, subprocess, sys
from datetime import datetime
import numpy as np
import pandas as pd

BASE_PANEL='panel_master_base.csv'
SOURCE='SOURCE_FINAL_so_hoa.xlsx'
REAL_PANEL='panel_master (1).csv'
ALIAS='panel_master.csv'
NETWORK='so phong chi nhanh.xlsx'
CODE_FILES=[
    '00_BUILD_FINAL_INPUTS.py','H1_H5_UNIFIED_HARMONIZED.py',
    'THREE_VARIABLE_SYMMETRIC_EVAL.py','THREE_VARIABLE_JOINT_CHECK_AUDITED.py',
    '06_MODEL_DIAGNOSTICS.py','07_ENDOGENEITY_ROBUSTNESS.py',
    '08_MODEL_FAMILIES_REDESIGNED.py']


def sha256(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for ch in iter(lambda:f.read(1<<20),b''): h.update(ch)
    return h.hexdigest()


def run(wd:Path, script:str, log:str, args=None):
    cmd=[sys.executable,script]+(args or [])
    proc=subprocess.run(cmd,cwd=wd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                        text=True,encoding='utf-8',errors='replace')
    (wd/log).write_text(proc.stdout,encoding='utf-8')
    print(proc.stdout)
    if proc.returncode:
        raise RuntimeError(f'{script} failed status={proc.returncode}; see {log}')
    print(f'[PASS] {script} -> {log}')


def load_base(wd:Path):
    p=wd/'H1_H5_UNIFIED_HARMONIZED.py'
    spec=importlib.util.spec_from_file_location('basepipe',p)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def validate_source_files(wd:Path):
    req=[BASE_PANEL,SOURCE]+CODE_FILES
    miss=[x for x in req if not (wd/x).exists()]
    if miss: raise FileNotFoundError(f'Missing required files: {miss}')


def audit(wd:Path):
    b=load_base(wd)
    dr,dw,_=b.build_analysis_data(wd/REAL_PANEL,wd/NETWORK)
    focal=['CASA','SW_delta','SW_stock','network_count_harmonized','branch_den','CI']+b.CTRL
    rows=[]; detail=[]
    for c in focal:
        miss=dw[c].isna()
        rows.append({'variable':c,'N_private_panel':len(dw),'missing_bank_years':int(miss.sum()),
                     'nonmissing_bank_years':int((~miss).sum()),'banks_total':int(dw.Mã.nunique()),
                     'banks_with_data':int(dw.loc[~miss,'Mã'].nunique()),
                     'banks_all_missing':';'.join(str(g) for g,s in dw.groupby('Mã')[c] if s.notna().sum()==0)})
        for _,r in dw.loc[miss,['Mã','year']].iterrows():
            detail.append({'variable':c,'Mã':r.Mã,'year':int(r.year)})
    pd.DataFrame(rows).to_csv(wd/'MASTER_INPUT_MISSINGNESS_SUMMARY.csv',index=False)
    pd.DataFrame(detail).to_csv(wd/'MASTER_INPUT_MISSINGNESS_DETAIL.csv',index=False)
    req=['CASA','SW_delta','SW_stock','CI','branch_den','network_count_harmonized']+b.CTRL
    common=dw.replace([np.inf,-np.inf],np.nan).dropna(subset=req)
    info={'private_panel_bank_years':int(len(dw)),'private_panel_banks':int(dw.Mã.nunique()),
          'common3_bank_years':int(len(common)),'common3_banks':int(common.Mã.nunique()),
          'common3_year_min':int(common.year.min()),'common3_year_max':int(common.year.max())}
    (wd/'MASTER_COMMON_SAMPLE.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    print('[AUDIT]',info)


def manifest(wd:Path):
    outputs=[
        BASE_PANEL,SOURCE,REAL_PANEL,ALIAS,NETWORK,'SOFTWARE_SOURCE_CLEANED.csv',
        'SOFTWARE_COVERAGE_26BANKS.csv','SOFTWARE_SOURCE_MERGE_AUDIT.csv',
        'H1_H5_results_harmonized.csv','THREE_VARIABLE_SYMMETRIC_RESULTS.csv',
        'THREE_VARIABLE_JOINT_RESULTS_RERUN.csv','MODEL_DIAGNOSTICS_RESULTS.csv',
        'ENDOGENEITY_ROBUSTNESS_RESULTS.csv','MASTER_INPUT_MISSINGNESS_SUMMARY.csv',
        'MASTER_INPUT_MISSINGNESS_DETAIL.csv','MASTER_COMMON_SAMPLE.json',
        'REDESIGNED_MODEL_RESULTS.csv','REDESIGNED_MODEL_DIAGNOSTICS.csv']+CODE_FILES
    rows=[]
    for name in outputs:
        p=wd/name
        if p.exists(): rows.append({'file':name,'bytes':p.stat().st_size,'sha256':sha256(p)})
    pd.DataFrame(rows).to_csv(wd/'FINAL_MANIFEST_SHA256.csv',index=False)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--workdir',default='.')
    ap.add_argument('--audit-only',action='store_true')
    args=ap.parse_args(); wd=Path(args.workdir).resolve()
    print(f'[MASTER FINAL] workdir={wd}')
    print(f'[MASTER FINAL] started={datetime.now().isoformat(timespec="seconds")}')
    validate_source_files(wd)
    run(wd,'00_BUILD_FINAL_INPUTS.py','MASTER_00_BUILD.log',
        ['--base-panel',BASE_PANEL,'--source',SOURCE,'--outdir','.'])
    audit(wd)
    if args.audit_only:
        manifest(wd); return
    run(wd,'H1_H5_UNIFIED_HARMONIZED.py','MASTER_01_H1_H5.log')
    run(wd,'THREE_VARIABLE_SYMMETRIC_EVAL.py','MASTER_02_SYMMETRIC.log')
    run(wd,'THREE_VARIABLE_JOINT_CHECK_AUDITED.py','MASTER_03_JOINT.log')
    run(wd,'06_MODEL_DIAGNOSTICS.py','MASTER_04_DIAGNOSTICS.log')
    run(wd,'07_ENDOGENEITY_ROBUSTNESS.py','MASTER_05_ENDOGENEITY_ROBUSTNESS.log')
    run(wd,'08_MODEL_FAMILIES_REDESIGNED.py','MASTER_06_REDESIGNED_MODELS.log')
    manifest(wd)
    print('\n'+'='*100+'\nFINAL MASTER PIPELINE COMPLETE\n'+'='*100)


if __name__=='__main__': main()
