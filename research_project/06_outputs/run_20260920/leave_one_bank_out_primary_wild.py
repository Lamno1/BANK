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

iv = load('inference_validation_wild', ANALYSIS / '09_INFERENCE_VALIDATION.py')
b = iv.b
panel = BASE / '01_data' / 'locked_inputs' / 'panel_master_FINAL.csv'
network = BASE / '01_data' / 'locked_inputs' / 'so_phong_chi_nhanh_FINAL.xlsx'
BOOT = 999
SEED = 20260920

dr, dw, _ = b.build_analysis_data(panel, network)
idc = dr.columns[0]
if dw.columns[0] != idc:
    dw = dw.rename(columns={dw.columns[0]: idc})
comp = dw if 'AssetCostShare_raw' in dw.columns else dw.merge(
    dr[[idc, 'year', 'AssetCostShare_raw']], on=[idc, 'year'],
    how='left', validate='one_to_one')
d, xvars = iv._prepare(comp, 'SW_stock', 'AssetCostShare_raw', False)
banks = sorted(d[idc].astype(str).unique())

def one(dsub, omitted):
    X, y, resid, beta, inv, cols, groups = iv._fit(dsub, 'AssetCostShare_raw', xvars)
    cov = iv._covariances(X, resid, inv, groups)
    j = cols.index('z_X')
    contrast = np.zeros(len(cols)); contrast[j] = 1
    se = float(np.sqrt(max(cov['cr2'][j, j], 0)))
    df = iv._satterthwaite(cov['cr2'], inv, cov['qg'], contrast)
    _, cr2_p, lo, hi = iv._p_interval(float(beta[j]), se, df)
    wild_p, _, _, reps = iv._wild_bootstrap(X, y, beta, inv, cols, groups, 'z_X', B=BOOT, seed=SEED)
    return {
        'omitted_bank': omitted,
        'coef': float(beta[j]), 'se_CR2': se, 'df_CR2': float(df),
        'p_CR2': float(cr2_p), 'ci_low': float(lo), 'ci_high': float(hi),
        'wild_p': float(wild_p), 'bootstrap_reps': int(reps),
        'N': int(cov['n']), 'G': int(cov['G']),
        'cr2_supported_5pct': bool(cr2_p < .05),
        'wild_supported_5pct': bool(wild_p < .05),
        'wild_supported_10pct': bool(wild_p < .10),
    }

rows = [one(d.copy(), '[NONE — FULL PRIMARY SAMPLE]')]
rows += [one(d[d[idc].astype(str) != bank].copy(), bank) for bank in banks]
res = pd.DataFrame(rows)
res.to_csv(OUTDIR / 'LEAVE_ONE_BANK_OUT_PRIMARY_WILD.csv', index=False)

loo = res[res['omitted_bank'] != '[NONE — FULL PRIMARY SAMPLE]']
tcb = loo[loo['omitted_bank'] == 'TCB'].iloc[0]
lines = [
    '# Leave-One-Bank-Out Wild-Cluster Diagnostic — Primary Composition Specification', '',
    'Specification and sample rules are identical to the locked primary composition model: `SW_stock → AssetCostShare_raw`, no `branch_den`, bank FE, year FE, locked controls, and CR2/wild inference routines reused from `09_INFERENCE_VALIDATION.py`.',
    f'Wild procedure: null-imposed Rademacher wild-cluster bootstrap, {BOOT} replications, seed {SEED}. This is a sensitivity diagnostic; TCB remains in the full sample.', '',
    '## Full sample and TCB omission', '',
    f"- Full sample: β={res.iloc[0]['coef']:.9f}; CR2 p={res.iloc[0]['p_CR2']:.9f}; wild p={res.iloc[0]['wild_p']:.9f}; df={res.iloc[0]['df_CR2']:.6f}; N={int(res.iloc[0]['N'])}; G={int(res.iloc[0]['G'])}.",
    f"- Omitting TCB: β={tcb['coef']:.9f}; CR2 p={tcb['p_CR2']:.9f}; wild p={tcb['wild_p']:.9f}; df={tcb['df_CR2']:.6f}; N={int(tcb['N'])}; G={int(tcb['G'])}.", '',
    '## Leave-one-bank-out wild results', '',
    '| Omitted bank | β | CR2 p | df | Wild p | N | G | Wild p<0.05 |',
    '|---|---:|---:|---:|---:|---:|---:|:---:|',
]
for _, r in loo.iterrows():
    lines.append(f"| {r['omitted_bank']} | {r['coef']:.9f} | {r['p_CR2']:.9f} | {r['df_CR2']:.6f} | {r['wild_p']:.9f} | {int(r['N'])} | {int(r['G'])} | {'yes' if r['wild_supported_5pct'] else 'no'} |")

wild_sig = int(loo['wild_supported_5pct'].sum())
cr2_sig = int(loo['cr2_supported_5pct'].sum())
lines += ['', '## Decision branches', '']
if bool(tcb['wild_supported_5pct']):
    lines.append('DECISION BRANCH 1: Wild-cluster inference remains significant after omitting TCB. The TCB fragility is primarily a CR2-Satterthwaite low-df sensitivity; no hypothesis or model restructuring is indicated by this diagnostic alone.')
else:
    lines.append('DECISION BRANCH 2: Wild-cluster inference also loses 5% significance after omitting TCB. The primary association is influence-sensitive under both inference references; any reframing requires a separate content decision and must not exclude TCB.')
lines.append(f'Across the 26 exclusions, CR2 retains 5% support in {cr2_sig}/26 cases and wild-cluster retains 5% support in {wild_sig}/26 cases.')

(OUTDIR / 'LEAVE_ONE_BANK_OUT_PRIMARY_WILD.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(res.to_string(index=False))
print('\nSaved:', OUTDIR / 'LEAVE_ONE_BANK_OUT_PRIMARY_WILD.csv')
print('Saved:', OUTDIR / 'LEAVE_ONE_BANK_OUT_PRIMARY_WILD.md')
