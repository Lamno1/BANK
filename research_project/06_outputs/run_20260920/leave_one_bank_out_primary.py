from pathlib import Path
import importlib.util
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
ANALYSIS = BASE / '02_code' / 'analysis'
OUTDIR = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

iv = load('inference_validation', ANALYSIS / '09_INFERENCE_VALIDATION.py')
b = iv.b
panel = BASE / '01_data' / 'locked_inputs' / 'panel_master_FINAL.csv'
network = BASE / '01_data' / 'locked_inputs' / 'so_phong_chi_nhanh_FINAL.xlsx'

dr, dw, thresholds = b.build_analysis_data(panel, network)
idc = dr.columns[0]
if dw.columns[0] != idc:
    dw = dw.rename(columns={dw.columns[0]: idc})
comp = dw if 'AssetCostShare_raw' in dw.columns else dw.merge(
    dr[[idc, 'year', 'AssetCostShare_raw']],
    on=[idc, 'year'], how='left', validate='one_to_one')

d, xvars = iv._prepare(comp, 'SW_stock', 'AssetCostShare_raw', False)
banks = sorted(d[idc].astype(str).unique())

def fit_row(dsub, omitted):
    X, y, resid, beta, inv, cols, groups = iv._fit(dsub, 'AssetCostShare_raw', xvars)
    cov = iv._covariances(X, resid, inv, groups)
    j = cols.index('z_X')
    se = float(np.sqrt(max(cov['cr2'][j, j], 0)))
    contrast = np.zeros(len(cols)); contrast[j] = 1
    df = iv._satterthwaite(cov['cr2'], inv, cov['qg'], contrast)
    t, p, lo, hi = iv._p_interval(float(beta[j]), se, df)
    return {
        'omitted_bank': omitted,
        'coef': float(beta[j]),
        'se_CR2': se,
        'df_CR2': float(df),
        't_CR2': float(t),
        'p_CR2': float(p),
        'ci_low': float(lo),
        'ci_high': float(hi),
        'N': int(cov['n']),
        'G': int(cov['G']),
        'sign_positive': bool(beta[j] > 0),
        'supported_5pct': bool(p < 0.05),
        'supported_10pct': bool(p < 0.10),
    }

rows = [fit_row(d[d[idc].astype(str) != bank].copy(), bank) for bank in banks]
full = fit_row(d.copy(), '[NONE — FULL PRIMARY SAMPLE]')
full['is_full_sample'] = True
for r in rows:
    r['is_full_sample'] = False
res = pd.DataFrame([full] + rows)
res.to_csv(OUTDIR / 'LEAVE_ONE_BANK_OUT_PRIMARY.csv', index=False)

loo = res[~res['is_full_sample']]
fullrow = res[res['is_full_sample']].iloc[0]
minr = loo.loc[loo['coef'].idxmin()]
maxr = loo.loc[loo['coef'].idxmax()]
minp = loo.loc[loo['p_CR2'].idxmin()]
maxp = loo.loc[loo['p_CR2'].idxmax()]
sign_flips = loo[loo['coef'] <= 0]
lost_5 = loo[~loo['supported_5pct']]
lost_10 = loo[~loo['supported_10pct']]

lines = [
    '# Leave-One-Bank-Out Audit — Primary Composition Specification', '',
    'Specification: `SW_stock → AssetCostShare_raw`, no `branch_den`; bank FE and year FE; locked controls; CR2-Satterthwaite inference.',
    'Source: locked `panel_master_FINAL.csv` and locked harmonized network input. This is a sensitivity audit only; no model, hypothesis, estimand, or inference protocol was changed.', '',
    '## Full-sample reference', '',
    f"- β={fullrow['coef']:.9f}; CR2 p={fullrow['p_CR2']:.9f}; df={fullrow['df_CR2']:.6f}; 95% CI [{fullrow['ci_low']:.9f}, {fullrow['ci_high']:.9f}]; N={int(fullrow['N'])}; G={int(fullrow['G'])}.", '',
    '## Leave-one-bank-out summary', '',
    f"- Coefficient range: [{minr['coef']:.9f}, {maxr['coef']:.9f}] (minimum when omitting {minr['omitted_bank']}; maximum when omitting {maxr['omitted_bank']}).",
    f"- CR2 p-value range: [{minp['p_CR2']:.9f}, {maxp['p_CR2']:.9f}] (minimum when omitting {minp['omitted_bank']}; maximum when omitting {maxp['omitted_bank']}).",
    f"- df range: [{loo['df_CR2'].min():.6f}, {loo['df_CR2'].max():.6f}].",
    f"- Sign flips: {len(sign_flips)} of {len(loo)} exclusions.",
    f"- Loss of 5% CR2 support: {len(lost_5)} of {len(loo)} exclusions.",
    f"- Loss of 10% CR2 support: {len(lost_10)} of {len(loo)} exclusions.", '',
    '## Bank-level results', '',
    '| Omitted bank | β | SE | df | CR2 p | 95% CI | N | G | Positive | Supported at 5% |',
    '|---|---:|---:|---:|---:|---|---:|---:|:---:|:---:|',
]
for _, r in loo.iterrows():
    lines.append(f"| {r['omitted_bank']} | {r['coef']:.9f} | {r['se_CR2']:.9f} | {r['df_CR2']:.6f} | {r['p_CR2']:.9f} | [{r['ci_low']:.9f}, {r['ci_high']:.9f}] | {int(r['N'])} | {int(r['G'])} | {'yes' if r['sign_positive'] else 'no'} | {'yes' if r['supported_5pct'] else 'no'} |")

lines += ['', '## Interpretation', '']
if len(sign_flips) == 0 and len(lost_5) == 0:
    lines.append('The primary coefficient remains positive and below the 5% CR2-Satterthwaite threshold after every single-bank omission. The primary association is therefore not dependent on one omitted bank in this leave-one-bank-out audit, subject to the small-cluster and associational limitations already documented.')
else:
    lines.append('At least one single-bank omission changes the sign or the 5% CR2-Satterthwaite classification. The primary result should be treated as influence-sensitive and the omitted-bank rows above must be discussed before submission.')

(OUTDIR / 'LEAVE_ONE_BANK_OUT_PRIMARY.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(res.to_string(index=False))
print('\nSaved:', OUTDIR / 'LEAVE_ONE_BANK_OUT_PRIMARY.csv')
print('Saved:', OUTDIR / 'LEAVE_ONE_BANK_OUT_PRIMARY.md')
