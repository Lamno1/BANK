# Execution report — 20 September 2026

## Status

The restored master pipeline and redesigned model-family module ran successfully with UTF-8 console output.

Execution bundle: `run_20260920/`

No traceback, error, or failed stage was found in the stage logs.

## Reproduction checks

- Private panel: 286 bank-years, 26 banks, 2015–2025.
- Software values rebuilt: 274 valid `SW_stock` and `SW_delta` observations.
- Network merge: 284/286 private bank-years matched; VBB 2015–2016 missing.
- Common focal-variable sample: 268 observations, 26 banks.
- All restored modules passed Python AST syntax validation.
- SHA-256 manifest generated for inputs, outputs, and analysis modules.

## Redesigned model results

- Aggregate CI: Stock remains non-significant (`p = 0.255`); Flow remains non-significant (`p = 0.214`).
- Scale sensitivity: `log1p(Stock)` and signed-log Flow remain non-significant for CI (`p = 0.280` and `p = 0.147` conditional on network).
- Composition: Stock is positively associated with `AssetCostShare` (`p = 0.005` conditional on network) and negatively associated with `StaffShare` (`p = 0.006`). These are composition associations, not causal substitution effects.
- Network outcome: Stock is negatively associated with log network count (`p = 0.006`), but this remains observational and should not be described as branch substitution caused by software.
- Post-2020 slope: Flow interaction is significant (`p = 0.006`), but this is a descriptive regime difference, not a COVID, policy, or treatment effect.

The full row-level results are in `REDESIGNED_MODEL_RESULTS.csv`; diagnostics are in `REDESIGNED_MODEL_DIAGNOSTICS.csv`.

## Interpretation lock

The preferred conclusion remains: recognized software stock is more consistently associated with operating-cost composition than with aggregate cost intensity. The rerun does not establish causal reconfiguration.
