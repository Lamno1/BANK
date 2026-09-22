# Leave-One-Bank-Out Wild-Cluster Diagnostic — Primary Composition Specification

Specification and sample rules are identical to the locked primary composition model: `SW_stock → AssetCostShare_raw`, no `branch_den`, bank FE, year FE, locked controls, and CR2/wild inference routines reused from `09_INFERENCE_VALIDATION.py`.
Wild procedure: null-imposed Rademacher wild-cluster bootstrap, 999 replications, seed 20260920. This is a sensitivity diagnostic; TCB remains in the full sample.

## Full sample and TCB omission

- Full sample: β=0.018455139; CR2 p=0.031314451; wild p=0.002000000; df=3.788478; N=270; G=26.
- Omitting TCB: β=0.016051045; CR2 p=0.238518739; wild p=0.002000000; df=2.376922; N=259; G=25.

## Leave-one-bank-out wild results

| Omitted bank | β | CR2 p | df | Wild p | N | G | Wild p<0.05 |
|---|---:|---:|---:|---:|---:|---:|:---:|
| ABB | 0.019281779 | 0.031730262 | 3.501453 | 0.001000000 | 259 | 25 | yes |
| ACB | 0.019178234 | 0.034700198 | 3.575278 | 0.001000000 | 259 | 25 | yes |
| BAB | 0.017947493 | 0.028862836 | 4.238212 | 0.005000000 | 259 | 25 | yes |
| BAOVIETBAN | 0.018001838 | 0.032284053 | 3.448276 | 0.003000000 | 259 | 25 | yes |
| BVB | 0.018227591 | 0.032981301 | 3.823300 | 0.003000000 | 261 | 25 | yes |
| EIB | 0.018689597 | 0.031243537 | 3.750925 | 0.003000000 | 259 | 25 | yes |
| HDB | 0.018335895 | 0.032736415 | 3.911312 | 0.003000000 | 260 | 25 | yes |
| KLB | 0.018035220 | 0.033177299 | 3.942611 | 0.002000000 | 259 | 25 | yes |
| LPB | 0.018592893 | 0.028654710 | 4.183451 | 0.003000000 | 260 | 25 | yes |
| MBB | 0.024449850 | 0.016058858 | 3.710380 | 0.003000000 | 259 | 25 | yes |
| MSB | 0.017994515 | 0.036621531 | 3.771214 | 0.003000000 | 259 | 25 | yes |
| NAB | 0.016921634 | 0.022290404 | 4.495669 | 0.004000000 | 261 | 25 | yes |
| NVB | 0.018851049 | 0.035915564 | 3.706552 | 0.004000000 | 259 | 25 | yes |
| OCB | 0.018486329 | 0.029867909 | 4.198047 | 0.005000000 | 260 | 25 | yes |
| PCB | 0.018506446 | 0.033193332 | 3.733532 | 0.003000000 | 262 | 25 | yes |
| PGB | 0.018520135 | 0.030206144 | 3.990810 | 0.003000000 | 259 | 25 | yes |
| SGB | 0.018434347 | 0.031050346 | 3.826948 | 0.004000000 | 260 | 25 | yes |
| SHB | 0.018104195 | 0.031289098 | 4.100755 | 0.005000000 | 259 | 25 | yes |
| SSB | 0.018352946 | 0.030838728 | 4.230489 | 0.005000000 | 260 | 25 | yes |
| STB | 0.018395661 | 0.039434806 | 3.694789 | 0.005000000 | 259 | 25 | yes |
| TCB | 0.016051045 | 0.238518739 | 2.376922 | 0.002000000 | 259 | 25 | yes |
| TPB | 0.018622620 | 0.023159389 | 4.341015 | 0.002000000 | 259 | 25 | yes |
| VAB | 0.018297461 | 0.030588394 | 3.927371 | 0.002000000 | 261 | 25 | yes |
| VBB | 0.018980794 | 0.023177011 | 3.997239 | 0.002000000 | 261 | 25 | yes |
| VIB | 0.017560407 | 0.039334929 | 3.907796 | 0.004000000 | 259 | 25 | yes |
| VPB | 0.018226011 | 0.033291112 | 3.778248 | 0.002000000 | 259 | 25 | yes |

## Decision branches

DECISION BRANCH 1: Wild-cluster inference remains significant after omitting TCB. The TCB fragility is primarily a CR2-Satterthwaite low-df sensitivity; no hypothesis or model restructuring is indicated by this diagnostic alone.
Across the 26 exclusions, CR2 retains 5% support in 25/26 cases and wild-cluster retains 5% support in 26/26 cases.
