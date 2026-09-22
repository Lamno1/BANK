# ERA Final Report — Software Capital & Cost Composition, Vietnamese Banks

## 1. Mandate

The user transferred the project from a Senior-Peer-Reviewer arrangement to a single End-to-End Research Agent (ERA) role, with explicit terms:
- New workspace (`10_era/`), the audited baseline (V11, `07_manuscript_reconstruction/`) left frozen and untouched.
- No internal adversarial self-check required before locking a claim.
- Causal gate open at the agent's own discretion, no external approval needed.
- Scope bounded to the existing Vietnamese-bank dataset; otherwise unrestricted on variables, methodology, hypotheses, and branches.

Everything below was produced under that mandate. Nothing in this report has been through the adversarial-review step the user explicitly waived; it should be read with that in mind.

## 2. What was explored and built

**New data source exploited:** `so phong chi nhanh.xlsx` sheet "Phần mềm máy vi tính," an annual software-amortization schedule by bank-year (2014-2025) that was present in the raw data folder but never incorporated into the locked panel. Coverage: 25 of 26 privately controlled bank clusters (VBB missing). Verified against the two pre-existing calibration points (VPB 2018 matched exactly at 7.71%; TCB 2018 matched closely at 8.76% vs. 8.86%).

**Core method throughout:** every test reused the locked `09_INFERENCE_VALIDATION.py` pipeline (`_prepare`, `_fit`, `_covariances`, `_satterthwaite`, `_wild_bootstrap`) and the locked `H1_H5_UNIFIED_HARMONIZED.py` helpers (`prep_fi`, `mm`, `z`, `CTRL`). No new estimator, no change to the locked data, no new specification family — only outcome/predictor substitutions (ex-software variants) and diagnostic decompositions on top of the existing design.

## 3. Findings, by thread

### 3.1 Ex-software decomposition (primary H4 result)
Removing the software-amortization component from AssetCost: coefficient retains ~65% of its original magnitude (0.012071 vs. 0.018455 without branch_den; 0.011664 vs. 0.018019 with branch_den). CR2-Satterthwaite weakens to borderline (p=0.057-0.072); wild-cluster bootstrap stays significant throughout (p<=0.006), including at every leave-one-bank-out configuration. **Conclusion: the composition association is not purely a mechanical accounting artifact, but roughly a third of its magnitude is.**

### 3.2 Why CR2 is fragile — the real mechanism
Cluster-influence decomposition of the CR2 variance revealed that **MBB, not TCB, is the single dominant cluster** (71% of variance in the full sample; TCB is a distant second at 11.6%). Removing TCB does not itself cause fragility — it removes MBB's main counterweight, concentrating variance in MBB to 92% and collapsing df from 3.79 to 2.38. Removing MBB instead simply hands the same ~71% dominance to TCB, with df barely moving (3.71). The two banks are exchanging the same structural role.

### 3.3 MBB 2025 verification
MBB's ~43% year-on-year total-asset growth in 2025 was cross-checked against an independent SHS analyst report (2024 base figure matched exactly) and press coverage (MB Bank independently reported as the fastest-growing asset base among Vietnam's "Big 5" in 2025, attributed to organic credit/CASA/funding-cost factors). The compulsory OceanBank/MBV transfer (Oct 2024) is real but its ~46 trillion VND scale explains only a minor fraction of the growth. **Conclusion: a genuine, externally verified economic event, not a data error — but a structurally exceptional bank-year.**

### 3.4 H4a — a different, opposite-direction divergence
H4a (Stock -> ln network) shows CR2 significant (p=0.013) but wild-cluster not (p=0.083) — the reverse of H4's pattern. Diagnosis: cluster influence is far more evenly spread than in H4 (top cluster LPB at 37%, not 70%+), so this is not a single-cluster-domination story. Instead, the wild-bootstrap's null-restricted residuals are concentrated in LPB (31% of total null RSS, driven by two poorly-fit early-year observations), widening the empirical bootstrap distribution to ~1.8x the CR2 SE. **Conclusion: here CR2 is likely the optimistic method; the existing "inference-sensitive" label is correct, now with a verified mechanism.**

### 3.5 H1, H2, H3, H5 sensitivity battery
- **H1 (CASA->CI), H5 (both size-interaction terms):** essentially unchanged under ex-software substitution — robust, not an accounting artifact.
- **H2 Flow baseline, H3, H4R-A(SW_delta):** already null/weak in the locked design, remain so (H3's wild-cluster p moves from 0.086 to 0.033, a boundary shift that does not change the CR2-based conclusion).
- **H2 Flow x Post-2020:** coefficient grows ~25% under ex-software CI, but CR2 weakens (p=0.0217 to 0.0754, df 7.18 to 4.17) while wild stays significant (p=0.002). Cluster decomposition attributes this to **VPB** (variance share 48% to 68%) — the same recurring pattern as H4/MBB, now involving the *other* directly-confirmed high-software-amortization bank.
- **H4(SW_delta)->AssetCostShare:** already "inference-sensitive," weakens further (coefficient to ~57%, CR2 loses significance too).
- **H4R-A(SW_stock)->NonAssetMinusAsset:** mirrors the primary H4 pattern exactly (~85% magnitude retained, CR2 borderline, wild robust).

### 3.6 Exogenous-variation search (causal-gate exploration)
Six candidates from Vietnamese banking regulation/markets were examined and rejected (full detail in `EXOGENOUS_VARIATION_SEARCH_LOG.md`): Basel II 2016 pilot cohort (self-selected), compulsory bank transfers (too few cases, selection-on-strength), Circular 09/2020 IT-security rule (nationwide-simultaneous), Decree 85/2016 information-system tiers (threshold doesn't bind in this sample), annual credit-growth quotas (directly CAMELS-based, i.e., health-based), and stock-exchange listing timing (voluntary, confounded with modernization ambition). All six fail via one of three recurring mechanisms (uniform nationwide policy / health-or-discretion-based selection / non-binding threshold). **The causal gate remains closed — a documented, bounded negative finding, not an unexamined default.**

## 4. What this changes about the paper's novelty tier

Assessed directly against the four-dimension novelty framework the user supplied (data / methodological / contextual / conceptual-mechanism novelty) and the four problem-type categories (theory testing, causal policy evaluation, risk/uncertainty optimization, development/structural issues):

- **No tier change.** The paper remains a Level-3 associational/measurement contribution, exactly as the project's own pre-ERA strategic assessment (Gate 2.0/2.2) already concluded.
- ERA's contribution is a **rigor and precision upgrade**, not a **novelty upgrade**: it quantifies how much of the primary effect is mechanical (~35%), identifies the true statistical drivers of small-cluster fragility (MBB, VPB, LPB — not just TCB), and closes off the causal-upgrade question with documented evidence rather than leaving it unexamined.
- The one dimension genuinely (if modestly) touched is **data novelty** — one more previously-unused source was incorporated. **Methodological, contextual, and conceptual/mechanism novelty are unchanged.** In particular, nothing here identifies an economic transmission channel (implementation cost vs. accounting recognition vs. organizational complementarity, etc.) — all mechanism work done was about the *statistical inference machinery*, not the *economic mechanism* the paper itself says it cannot distinguish.
- Moving into the higher-novelty categories (causal identification, new mechanism) would require **new primary data** (project-level IT implementation records, or a genuine natural experiment not identified in this search) — a materially larger undertaking than reprocessing existing files.

## 5. Current state of artifacts

| File | Status |
|---|---|
| `07_manuscript_reconstruction/FINAL_SUBMISSION_CANDIDATE_SCENARIO_A_V11.docx` | Frozen, untouched, submission-track baseline (per Senior-Reviewer track) |
| `10_era/ERA_V12_EX_SOFTWARE_MBB_TCB_DISCLOSURE.docx` | 24 pages; built from V11 + all findings in §3.1-3.6 inserted at Abstract/Results(6.2b, new)/Discussion/Limitations/Conclusion/Table 0, plus Tables EX-1/EX-2/EX-3. Rendered and visually QA'd; two structural bugs (table/caption ordering, table width overflow) were introduced and self-corrected during construction. |
| `10_era/EXOGENOUS_VARIATION_SEARCH_LOG.md` | Full causal-gate search record |
| `10_era/*.py`, `*.csv` | All underlying scripts and raw diagnostic outputs (leave-one-out tables, influence decompositions, wild-bootstrap draws, etc.), left in place for traceability |

## 6. Honest limitations of this ERA pass

- No adversarial self-check was applied to any of the above, per the user's explicit instruction — findings are reported as produced, not independently re-attacked.
- The exogenous-variation search relied on secondary Vietnamese financial press and legal-database summaries, not primary legal texts read in full; treat circular-level factual claims as reasonably but not perfectly reliable.
- ERA_V12 is a candidate document, not a re-audited replacement for V11 — it has not gone through the multi-round verification-by-reading-nguyên-văn discipline that V11's content underwent before this session began.
