# Final reproducibility code — 26-bank software-capital panel

## Locked inputs
Place these files in the same working directory as the code:

- `panel_master_base.csv` — the financial panel before the final software refresh.
- `SOURCE_FINAL_so_hoa.xlsx` — the final digitized source workbook.

## Locked source rule
- Software sheet: `Phần mềm máy vi tính`.
- Values exactly equal to **0 or 1 are NA** before constructing software variables.
- `SW_stock = Nguyên giá cuối kì`.
- `SW_delta = Nguyên giá cuối kì - Nguyên giá đầu kì` in the same year, only when both are valid.
- Network comes from the `số phòng chi nhánh` sheet in the same final workbook.

## Run
```bash
python MASTER_REPLICATION_FINAL.py --workdir .
```

The master rebuilds final inputs and executes:
1. `00_BUILD_FINAL_INPUTS.py`
2. `H1_H5_UNIFIED_HARMONIZED.py`
3. `THREE_VARIABLE_SYMMETRIC_EVAL.py`
4. `THREE_VARIABLE_JOINT_CHECK_AUDITED.py`
5. `06_MODEL_DIAGNOSTICS.py`
6. `07_ENDOGENEITY_ROBUSTNESS.py`

## Core identification statement
The code estimates **conditional associations**, not causal effects. Bank FE and year FE remove time-invariant bank heterogeneity and common year shocks; CR2 improves small-cluster inference. Lead falsification and bank-specific trends test selected alternative explanations. The lag-based control-function diagnostic indicates an endogeneity concern for `SW_delta`, while distributed-lag tests warn that lagged software flow does not satisfy a clean exclusion restriction. No external/quasi-experimental instrument is imposed.
