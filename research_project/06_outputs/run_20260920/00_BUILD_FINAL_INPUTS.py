#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
00_BUILD_FINAL_INPUTS.py
Rebuild the final software variables from the locked source workbook and prepare
canonical inputs for the replication pipeline.

Locked source protocol
----------------------
- Software source sheet: "Phần mềm máy vi tính".
- SW_stock = "Nguyên giá cuối kì" (gross software cost at year-end).
- SW_delta = "Nguyên giá cuối kì" - "Nguyên giá đầu kì" in the SAME year.
- Any software source value exactly equal to 0 or 1 is treated as missing (NA)
  BEFORE SW_stock/SW_delta are constructed.
- SW_delta is missing whenever either beginning or ending gross value is missing.
- Network source is the "số phòng chi nhánh" sheet in the same final workbook.
  The whole source workbook is copied to `so phong chi nhanh.xlsx`; the modeling
  code locates the network sheet by its column names.

The script overwrites SW_stock/SW_delta from the final source for every matched
bank-year; it does not impute software values.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import shutil
import unicodedata
import numpy as np
import pandas as pd


def norm_text(x: object) -> str:
    s = '' if x is None else str(x)
    s = unicodedata.normalize('NFC', s).strip().lower()
    s = ' '.join(s.split())
    return s


def _find_software_sheet(xlsx: Path) -> str:
    xls = pd.ExcelFile(xlsx)
    # Prefer the locked canonical sheet name. The land-use-rights sheet has the
    # same accounting row labels and must never be mistaken for software.
    if 'Phần mềm máy vi tính' in xls.sheet_names:
        return 'Phần mềm máy vi tính'
    for sh in xls.sheet_names:
        tmp = pd.read_excel(xlsx, sheet_name=sh, nrows=20)
        cols = [norm_text(c) for c in tmp.columns]
        if 'mã' in cols and any('attribute' in c for c in cols):
            vals = tmp.astype(str).apply(lambda c: c.str.lower().str.contains('nguyên giá cuối', na=False)).any().any()
            if vals:
                return sh
    if 'Phần mềm máy vi tính' in xls.sheet_names:
        return 'Phần mềm máy vi tính'
    raise ValueError('Could not locate the software source sheet.')


def load_clean_software(source_xlsx: Path) -> pd.DataFrame:
    sh = _find_software_sheet(source_xlsx)
    raw = pd.read_excel(source_xlsx, sheet_name=sh)
    raw.columns = [str(c).strip() for c in raw.columns]
    code_col = next(c for c in raw.columns if norm_text(c) == 'mã')
    attr_col = next(c for c in raw.columns if 'attribute' in norm_text(c))
    name_cols = [c for c in raw.columns if norm_text(c) in ('tên công ty','ten cong ty')]
    name_col = name_cols[0] if name_cols else None

    year_cols = []
    for c in raw.columns:
        try:
            y = int(str(c).strip())
        except Exception:
            continue
        if 2000 <= y <= 2100:
            year_cols.append((c,y))
    if not year_cols:
        raise ValueError('No annual columns found in software source.')

    raw[code_col] = raw[code_col].astype(str).str.strip()
    raw['_attr'] = raw[attr_col].map(norm_text)
    end_mask = raw['_attr'].str.startswith('nguyên giá cuối kì') | raw['_attr'].str.startswith('nguyên giá cuối kỳ')
    beg_mask = raw['_attr'].str.startswith('nguyên giá đầu kì') | raw['_attr'].str.startswith('nguyên giá đầu kỳ')
    if end_mask.sum() == 0 or beg_mask.sum() == 0:
        raise ValueError('Could not locate beginning/end gross software rows.')

    pieces=[]
    for label, mask in [('gross_end', end_mask), ('gross_begin', beg_mask)]:
        part = raw.loc[mask, [code_col] + ([name_col] if name_col else []) + [c for c,_ in year_cols]].copy()
        long = part.melt(id_vars=[code_col] + ([name_col] if name_col else []),
                         value_vars=[c for c,_ in year_cols], var_name='_year_col', value_name=label)
        ymap = {str(c): y for c,y in year_cols}
        long['year'] = long['_year_col'].astype(str).map(ymap).astype(int)
        long = long.drop(columns=['_year_col'])
        long = long.rename(columns={code_col:'Mã'})
        if name_col:
            long = long.rename(columns={name_col:'Tên công ty'})
        pieces.append(long)

    keys=['Mã','year'] + (['Tên công ty'] if name_col else [])
    sw = pieces[0].merge(pieces[1], on=keys, how='outer', validate='one_to_one')
    for c in ['gross_end','gross_begin']:
        sw[c] = pd.to_numeric(sw[c], errors='coerce')
        sw.loc[sw[c].isin([0,1]), c] = np.nan
    sw['SW_stock'] = sw['gross_end']
    sw['SW_delta'] = sw['gross_end'] - sw['gross_begin']
    sw.loc[sw[['gross_end','gross_begin']].isna().any(axis=1), 'SW_delta'] = np.nan
    sw['Mã'] = sw['Mã'].astype(str).str.strip()
    return sw.sort_values(['Mã','year']).reset_index(drop=True)


def build_panel(base_panel: Path, source_xlsx: Path, outdir: Path) -> pd.DataFrame:
    outdir.mkdir(parents=True, exist_ok=True)
    panel = pd.read_csv(base_panel)
    if not {'Mã','year'}.issubset(panel.columns):
        raise KeyError('Base panel must contain Mã and year.')
    panel['Mã'] = panel['Mã'].astype(str).str.strip()
    panel['year'] = pd.to_numeric(panel['year'], errors='raise').astype(int)

    sw = load_clean_software(source_xlsx)
    sw.to_csv(outdir/'SOFTWARE_SOURCE_CLEANED.csv', index=False)

    old = panel[['Mã','year'] + [c for c in ['SW_stock','SW_delta'] if c in panel.columns]].copy()
    m = panel.drop(columns=[c for c in ['SW_stock','SW_delta'] if c in panel.columns]).merge(
        sw[['Mã','year','SW_stock','SW_delta']], on=['Mã','year'], how='left', validate='one_to_one')

    # Overlap audit before replacement.
    aud=[]
    if 'SW_stock' in old.columns:
        a=old.merge(sw[['Mã','year','SW_stock','SW_delta']], on=['Mã','year'], how='left', suffixes=('_old','_new'))
        for v in ['SW_stock','SW_delta']:
            both=a[f'{v}_old'].notna() & a[f'{v}_new'].notna()
            diff=(a.loc[both,f'{v}_old']-a.loc[both,f'{v}_new']).abs()
            aud.append({'variable':v,'old_nonmissing':int(a[f'{v}_old'].notna().sum()),
                        'new_nonmissing':int(a[f'{v}_new'].notna().sum()),
                        'overlap_nonmissing':int(both.sum()),
                        'overlap_mismatches_gt_1e-9':int((diff>1e-9).sum()),
                        'max_abs_difference':float(diff.max()) if len(diff) else np.nan})
    pd.DataFrame(aud).to_csv(outdir/'SOFTWARE_SOURCE_MERGE_AUDIT.csv',index=False)

    # Canonical aliases expected by downstream scripts.
    m.to_csv(outdir/'panel_master (1).csv', index=False)
    m.to_csv(outdir/'panel_master.csv', index=False)

    # The network loader searches by sheet/column content, so retaining the complete
    # locked source workbook avoids any manual re-export or version mixing.
    shutil.copy2(source_xlsx, outdir/'so phong chi nhanh.xlsx')

    private = m[m['SOE'].eq(0)].copy() if 'SOE' in m.columns else m.copy()
    cov = (private.groupby('Mã')
           .agg(N_years=('year','size'),
                SW_stock_nonmissing=('SW_stock','count'),
                SW_delta_nonmissing=('SW_delta','count'),
                first_stock_year=('year', lambda s: int(s[private.loc[s.index,'SW_stock'].notna()].min()) if private.loc[s.index,'SW_stock'].notna().any() else np.nan),
                last_stock_year=('year', lambda s: int(s[private.loc[s.index,'SW_stock'].notna()].max()) if private.loc[s.index,'SW_stock'].notna().any() else np.nan))
           .reset_index())
    cov.to_csv(outdir/'SOFTWARE_COVERAGE_26BANKS.csv', index=False)

    print(f'[BUILD] panel rows={len(m)}, private rows={len(private)}, private banks={private.Mã.nunique()}')
    print(f'[BUILD] valid SW_stock={private.SW_stock.notna().sum()}/{len(private)}; banks with data={private.loc[private.SW_stock.notna(),"Mã"].nunique()}')
    print(f'[BUILD] valid SW_delta={private.SW_delta.notna().sum()}/{len(private)}; banks with data={private.loc[private.SW_delta.notna(),"Mã"].nunique()}')
    return m


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base-panel', default='panel_master_base.csv')
    ap.add_argument('--source', default='SOURCE_FINAL_so_hoa.xlsx')
    ap.add_argument('--outdir', default='.')
    args=ap.parse_args()
    build_panel(Path(args.base_panel), Path(args.source), Path(args.outdir))


if __name__=='__main__':
    main()
