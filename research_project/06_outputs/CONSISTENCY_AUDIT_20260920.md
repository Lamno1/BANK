# Manuscript–rerun consistency audit

Compared `DIGITAL_CAPITAL_BANK_RECONFIGURATION_FINAL_MANUSCRIPT.docx` with the successful execution bundle in `run_20260920/`.

## Numerical results that match

The following values match the manuscript to the displayed precision:

- 26 private banks, 2015–2025, 286 private bank-years.
- 274/286 valid `SW_stock` and `SW_delta` observations.
- 284/286 network matches, with VBB 2015–2016 missing.
- Common `CASA + Flow + Stock` sample: 268 observations.
- H1 CASA → CI: `0.001609`, `p = 0.0004`, `N = 273`, `G = 26`.
- H2 Flow baseline: `0.000394`, `p = 0.2137`, `N = 271`.
- H2 Flow × Post2020: `-0.002284`, `p = 0.0069`.
- H3 Stock baseline: `-0.000609`, `p = 0.2547`.
- H4 Stock absolute contrast: `-0.000980`, `p = 0.0139`, `N = 270`.
- H4 Stock asset-cost share: `0.018019`, `p = 0.0052`.
- H4 Stock staff component: `-0.000942`, `p = 0.0033`.
- H4a Stock log network: `-0.074538`, `p = 0.0058`.
- H4 Flow asset-cost share: `0.009539`, `p = 0.0073`.
- H4a Flow log network: `-0.055280`, `p = 0.0022`.
- H5 Stock × BIG: `-0.008353`, `p = 0.0254`.
- H5 Stock × continuous size: `-0.002902`, `p = 0.0056`.
- Control-function lag coefficient: approximately `0.7299`, `p = 0.00000318`.
- Residual inclusion: `0.000923`, `p = 0.00014139`.
- Distributed-lag joint test: `F = 12.1131`, `p = 0.00020979`.
- Stock bank-trend robustness: absolute contrast `-0.002367`, `p = 0.0153`; asset share `0.032215`, `p = 0.0224`; staff `p = 0.2883`; network `p = 0.2597`.
- Flow future-lead joint tests and Stock lead warning match the manuscript's reported values.

## Textual or packaging inconsistencies

### 1. “Unbalanced panel” is inaccurate for the source panel

The private source panel is observed as 26 × 11 = 286 rows. It is balanced at the panel level. Individual estimation samples become unbalanced because software, network, and accounting variables have missing observations. The abstract should say “balanced private-bank source panel with variable-specific estimation samples” or equivalent.

### 2. The manuscript does not include the redesigned model-family results

The new results for `log1p(SW_stock)`, signed-log Flow, `StaffShare`, `OtherShare`, and separate network-control specifications are not in the original manuscript. They are new outputs, not contradictions. They need a clearly labelled robustness/design-revision section before being cited in the paper.

### 3. Appendix D code metadata is stale

The manuscript lists old file sizes and SHA prefixes and does not list `08_MODEL_FAMILIES_REDESIGNED.py`. The restored executable files and current manifest are in `run_20260920`; Appendix D must be regenerated from `FINAL_MANIFEST_SHA256.csv` before submission.

### 4. Reproducibility claim now applies to the new execution bundle, not the original delivery

The successful rerun verifies the reconstructed bundle. The original `bản nộp` directory still contains the concatenated source artifact and not the complete executable package. The manuscript should point to the reconstructed package or the files should be promoted into the official submission package.

### 5. Software-validity wording should match code exactly

The manuscript says valid software components are `>1` and non-missing. The code specifically converts values exactly equal to 0 or 1 to missing. The observed source values do not create a numerical difference here, but the rule should be written identically in both places.

## Verdict

**Canonical reported numbers: MATCH.**

**New redesigned results: NOT YET INCORPORATED into the manuscript.**

**Packaging, panel-description wording, and Appendix D: NEED UPDATE.**
