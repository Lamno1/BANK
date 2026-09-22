#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Redesigned model families for the bank-year association study.

The redesign separates aggregate intensity, cost composition, network outcomes,
scale sensitivity, and descriptive post-2020 slope heterogeneity. It does not
claim causal identification and treats the lag/control-function output as a
diagnostic only.
"""
from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
OUT = BASE
SRC = BASE / 'H1_H5_UNIFIED_HARMONIZED.py'
spec = importlib.util.spec_from_file_location('basepipe_redesigned', SRC)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

ID = 'Mã'
CTRL = b.CTRL
ROWS = []


def add(family, specification, predictor, outcome, role, q, res, note=''):
    ROWS.append({
        'family': family, 'specification': specification, 'predictor': predictor,
        'outcome': outcome, 'role': role, 'coef': q.get('coef', np.nan),
        'se_CR2': q.get('se', np.nan), 't': q.get('t', np.nan),
        'p_CR2': q.get('p', np.nan), 'N': res.get('_N', np.nan),
        'G': res.get('_G', np.nan), 'note': note
    })


def prepare(df, predictor, outcome, include_network=False):
    req = [predictor, outcome] + CTRL
    if include_network:
        req.append('branch_den')
    d = df.replace([np.inf, -np.inf], np.nan).dropna(subset=req).copy()
    d['z_X'] = b.z(d[predictor])
    x = ['z_X']
    if include_network:
        d['z_Branch'] = b.z(d['branch_den'])
        x.append('z_Branch')
    for c in CTRL:
        d['z_' + c] = b.z(d[c])
        x.append('z_' + c)
    return d, x


def estimate_intensity(dw):
    for predictor, label, role in [
        ('SW_stock', 'Software Stock', 'PRIMARY'),
        ('SW_delta', 'Software Flow', 'SECONDARY'),
    ]:
        for with_network, spec_name in [(False, 'without_network_control'),
                                        (True, 'conditional_on_network')]:
            d, x = prepare(dw, predictor, 'CI', with_network)
            r = b.ols_cr2(d, 'CI', x, return_full=True)
            add('aggregate_intensity', spec_name, predictor, 'CI', role,
                r['z_X'], r,
                'Conditional association; network control changes the estimand.'
                if with_network else 'Broader conditional association.')


def estimate_scale_sensitivity(dw):
    d = dw.replace([np.inf, -np.inf], np.nan).copy()
    d['stock_log1p'] = np.log1p(d['SW_stock'].clip(lower=0))
    d['flow_signed_log'] = np.sign(d['SW_delta']) * np.log1p(d['SW_delta'].abs())
    for predictor, label in [('stock_log1p', 'log1p software stock'),
                             ('flow_signed_log', 'signed log software flow')]:
        for with_network, spec_name in [(False, 'scale_without_network'),
                                        (True, 'scale_conditional_on_network')]:
            d2, x = prepare(d, predictor, 'CI', with_network)
            r = b.ols_cr2(d2, 'CI', x, return_full=True)
            add('scale_sensitivity', spec_name, label, 'CI', 'SENSITIVITY',
                r['z_X'], r,
                'Alternative scale transform; not substituted for the accounting-level baseline.')


def estimate_composition(dr, dw):
    raw = dr[[ID, 'year', 'CI_raw', 'Staff_raw', 'AssetCost_raw',
              'Other_raw', 'NonAssetMinusAsset_raw', 'AssetCostShare_raw']].copy()
    raw['StaffShare_raw'] = raw['Staff_raw'] / raw['CI_raw']
    raw['OtherShare_raw'] = raw['Other_raw'] / raw['CI_raw']
    d = dw.drop(columns=[c for c in raw.columns if c not in [ID, 'year'] and c in dw.columns],
                errors='ignore').merge(raw, on=[ID, 'year'], how='left', validate='one_to_one')
    outcomes = [
        ('AssetCostShare_raw', 'AssetCostShare', 'PRIMARY'),
        ('StaffShare_raw', 'StaffShare', 'SECONDARY'),
        ('OtherShare_raw', 'OtherShare', 'SECONDARY'),
        ('NonAssetMinusAsset_raw', 'NonAssetMinusAsset', 'SECONDARY'),
    ]
    for predictor, label, role in [('SW_stock', 'Software Stock', 'PRIMARY'),
                                   ('SW_delta', 'Software Flow', 'SECONDARY')]:
        for yvar, outcome, out_role in outcomes:
            for with_network, spec_name in [(False, 'composition_without_network'),
                                            (True, 'composition_conditional_on_network')]:
                d2, x = prepare(d, predictor, yvar, with_network)
                r = b.ols_cr2(d2, yvar, x, return_full=True)
                add('composition', spec_name, predictor, outcome,
                    role if out_role == 'PRIMARY' else out_role, r['z_X'], r,
                    'Shares sum to one; component coefficients are not independent evidence.'
                    if outcome in ('StaffShare', 'OtherShare') else
                    'Primary composition outcome.' if outcome == 'AssetCostShare' else
                    'Accounting contrast; secondary to the primary share.')


def estimate_network(dr, dw):
    for predictor, label, role in [('SW_stock', 'Software Stock', 'PRIMARY'),
                                   ('SW_delta', 'Software Flow', 'SECONDARY')]:
        req = [predictor, 'network_count_harmonized', 'ta'] + CTRL
        d = dw.replace([np.inf, -np.inf], np.nan).dropna(subset=req).copy()
        d = d[d['network_count_harmonized'] > 0].copy()
        d['lnNetwork'] = np.log(d['network_count_harmonized'])
        d2, x = prepare(d, predictor, 'lnNetwork', False)
        r = b.ols_cr2(d2, 'lnNetwork', x, return_full=True)
        add('network_outcome', 'network_as_outcome', predictor,
            'ln(harmonized network count)', role, r['z_X'], r,
            'Network is the outcome; branch_den is not included as a control.')


def estimate_temporal(dw):
    for predictor, label, role in [('SW_stock', 'Software Stock', 'PRIMARY'),
                                   ('SW_delta', 'Software Flow', 'SECONDARY')]:
        d, x = prepare(dw, predictor, 'CI', False)
        d['Post2020'] = (d['year'] >= 2020).astype(int)
        d['XxPost2020'] = d['z_X'] * d['Post2020']
        r = b.ols_cr2(d, 'CI', x + ['Post2020', 'XxPost2020'], return_full=True)
        add('temporal_heterogeneity', 'descriptive_post2020_slope', predictor,
            'CI', role, r['XxPost2020'], r,
            'Descriptive slope change; not a treatment effect or COVID/policy estimate.')


def diagnostics(dw):
    d = dw.copy()
    stock_ta = d[['SW_stock', 'ta']].corr().iloc[0, 1]
    d['stock_ta_ratio'] = d['SW_stock'] / d['ta']
    return pd.DataFrame([{
        'metric': 'raw_corr_SW_stock_total_assets', 'value': stock_ta,
        'note': 'Scale diagnostic; motivates alternative transforms.'
    }, {
        'metric': 'negative_SW_delta_private_rows',
        'value': int((d['SW_delta'] < 0).sum()),
        'note': 'Flow is a signed change in recognized gross software cost.'
    }, {
        'metric': 'private_panel_rows', 'value': len(d),
        'note': '26 banks x 11 observed years.'
    }, {
        'metric': 'private_panel_banks', 'value': d[ID].nunique(),
        'note': 'Bank clusters.'
    }])


def main():
    dr, dw, _ = b.build_analysis_data(BASE / 'panel_master (1).csv', BASE / 'so phong chi nhanh.xlsx')
    estimate_intensity(dw)
    estimate_scale_sensitivity(dw)
    estimate_composition(dr, dw)
    estimate_network(dr, dw)
    estimate_temporal(dw)
    pd.DataFrame(ROWS).to_csv(OUT / 'REDESIGNED_MODEL_RESULTS.csv', index=False)
    diagnostics(dw).to_csv(OUT / 'REDESIGNED_MODEL_DIAGNOSTICS.csv', index=False)
    print(f'Saved {OUT / "REDESIGNED_MODEL_RESULTS.csv"}')
    print(f'Saved {OUT / "REDESIGNED_MODEL_DIAGNOSTICS.csv"}')


if __name__ == '__main__':
    main()
