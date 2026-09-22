"""
EXPLORATORY FEASIBILITY CHECK ONLY - not part of the locked/frozen project.

Question: if H5 (scale boundary condition) is re-specified on AssetCostShare_raw
(the primary H4 composition outcome) instead of CI, using the project's own
PRIMARY no-branch_den specification and CR2-Satterthwaite inference engine
(09_INFERENCE_VALIDATION.py), is the SW_stock x Size interaction plausible
(sign, magnitude, significance) before anyone commits to rewriting the manuscript?

Does NOT modify any file under D:\BANK\research_project. Reuses the project's
own locked data loader (H1_H5_UNIFIED_HARMONIZED.build_analysis_data) and its
own CR2-Satterthwaite + wild-cluster-bootstrap inference engine
(09_INFERENCE_VALIDATION._fit/_covariances/_satterthwaite/_p_interval/_wild_bootstrap)
so results are apples-to-apples with the manuscript's headline numbers
(primary: beta=0.018455, CR2-Satt p=0.0313).
"""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(r"D:\BANK\research_project")
ANALYSIS = BASE / "02_code" / "analysis"
PANEL = BASE / "01_data" / "locked_inputs" / "panel_master_FINAL.csv"
NETWORK = BASE / "01_data" / "locked_inputs" / "so_phong_chi_nhanh_FINAL.xlsx"
SEED = 20260920
BOOT = 999


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


b = load("base_model", ANALYSIS / "H1_H5_UNIFIED_HARMONIZED.py")
iv = load("inference_validation", ANALYSIS / "09_INFERENCE_VALIDATION.py")


def fit_generic(d, yvar, xvars):
    """Same machinery as iv._fit/_covariances but returns everything needed
    to build custom linear contrasts (interaction slopes at small/large size)."""
    X, y, resid, beta, inv, cols, groups = iv._fit(d, yvar, xvars)
    cov = iv._covariances(X, resid, inv, groups)
    return {"X": X, "y": y, "resid": resid, "beta": beta, "inv": inv,
            "cols": cols, "groups": groups, "cov": cov, "d": d}


def contrast_report(fit, weights, label):
    beta, inv, cols, cov = fit["beta"], fit["inv"], fit["cols"], fit["cov"]
    a = np.zeros(len(cols))
    for var, w in weights.items():
        a[cols.index(var)] = w
    est = float(a @ beta)
    V = cov["cr2"]
    se = float(np.sqrt(max(a @ V @ a, 0.0)))
    df = iv._satterthwaite(V, inv, cov["qg"], a)
    t, p, lo, hi = iv._p_interval(est, se, df)
    return {"label": label, "coef": est, "se_CR2": se, "df_CR2": df,
            "t_CR2": t, "p_CR2": p, "ci_low": lo, "ci_high": hi}


def wild_p_for_contrast(fit, weights):
    """Wild-cluster bootstrap p-value for an arbitrary linear contrast,
    reusing iv._wild_bootstrap's null-imposed Rademacher design but generalized
    to a combination of columns rather than a single named column."""
    X, y, beta, inv, cols, groups = fit["X"], fit["y"], fit["beta"], fit["inv"], fit["cols"], fit["groups"]
    a = np.zeros(len(cols))
    for var, w in weights.items():
        a[cols.index(var)] = w
    keep = np.ones(len(cols), dtype=bool)
    for i, w in enumerate(a):
        if w != 0:
            keep[i] = False
    X0 = X[:, keep]
    b0 = np.linalg.pinv(X0.T @ X0) @ X0.T @ y
    fitted0 = X0 @ b0
    u0 = y - fitted0
    uniq = np.unique(groups)
    rng = np.random.default_rng(SEED)
    obs = float(a @ beta)
    draws = np.empty(BOOT)
    for z in range(BOOT):
        signs = {g: (1.0 if rng.integers(0, 2) else -1.0) for g in uniq}
        yb = fitted0 + np.array([u0[i] * signs[groups[i]] for i in range(len(y))])
        bb = inv @ X.T @ yb
        draws[z] = float(a @ bb)
    p = (1 + np.sum(np.abs(draws) >= abs(obs))) / (BOOT + 1)
    return p


def main():
    dr, dw, thresholds = b.build_analysis_data(PANEL, NETWORK)
    idc = dr.columns[0]
    if dw.columns[0] != idc:
        dw = dw.rename(columns={dw.columns[0]: idc})
    comp = dw if "AssetCostShare_raw" in dw.columns else dw.merge(
        dr[[idc, "year", "AssetCostShare_raw"]], on=[idc, "year"], how="left", validate="one_to_one")

    # --- 0. Sanity check: reproduce the manuscript's PRIMARY H4 headline number ---
    d0, x0 = iv._prepare(comp, "SW_stock", "AssetCostShare_raw", with_branch=False)
    fit0 = fit_generic(d0, "AssetCostShare_raw", x0)
    r0 = contrast_report(fit0, {"z_X": 1.0}, "H4 PRIMARY reproduction: SW_stock -> AssetCostShare_raw")
    print("=" * 100)
    print("SANITY CHECK (should match manuscript primary: beta~0.018455, CR2-Satt p~0.0313)")
    print(f"  beta={r0['coef']:+.9f}  CR2-Satt p={r0['p_CR2']:.6f}  df={r0['df_CR2']:.4f}  "
          f"N={fit0['cov']['n']}  G={fit0['cov']['G']}")

    # --- 1. H5-on-composition: continuous contemporaneous size interaction ---
    d1, x1 = iv._prepare(comp, "SW_stock", "AssetCostShare_raw", with_branch=False)
    d1["z_X_x_zlnTA"] = d1["z_X"] * d1["z_lnTA"]
    x1c = x1 + ["z_X_x_zlnTA"]
    fit1 = fit_generic(d1, "AssetCostShare_raw", x1c)
    r1 = contrast_report(fit1, {"z_X_x_zlnTA": 1.0}, "H5 continuous: SW_stock x z_lnTA -> AssetCostShare_raw")
    wp1 = wild_p_for_contrast(fit1, {"z_X_x_zlnTA": 1.0})
    print("\n" + "=" * 100)
    print("H5 (composition, continuous contemporaneous size interaction)")
    print(f"  interaction beta={r1['coef']:+.9f}  CR2-Satt p={r1['p_CR2']:.6f}  df={r1['df_CR2']:.4f}  wild-cluster p={wp1:.6f}")
    print(f"  N={fit1['cov']['n']}  G={fit1['cov']['G']}")
    for size_z, tag in [(-1.0, "-1SD size"), (0.0, "mean size"), (1.0, "+1SD size")]:
        rr = contrast_report(fit1, {"z_X": 1.0, "z_X_x_zlnTA": size_z}, f"marginal slope @ {tag}")
        print(f"    slope @ {tag:12s}: beta={rr['coef']:+.9f}  CR2-Satt p={rr['p_CR2']:.6f}")

    # --- 2. H5-on-composition: BIG (median split) contemporaneous size, matching original H5 style ---
    d2, x2 = iv._prepare(comp, "SW_stock", "AssetCostShare_raw", with_branch=False)
    med = d2["lnTA"].median()
    d2["BIG"] = (d2["lnTA"] > med).astype(int)
    d2["z_X_x_BIG"] = d2["z_X"] * d2["BIG"]
    x2c = x2 + ["BIG", "z_X_x_BIG"]
    fit2 = fit_generic(d2, "AssetCostShare_raw", x2c)
    r2 = contrast_report(fit2, {"z_X_x_BIG": 1.0}, "H5 BIG: SW_stock x BIG_it -> AssetCostShare_raw")
    wp2 = wild_p_for_contrast(fit2, {"z_X_x_BIG": 1.0})
    small = contrast_report(fit2, {"z_X": 1.0}, "slope | small bank-year")
    large = contrast_report(fit2, {"z_X": 1.0, "z_X_x_BIG": 1.0}, "slope | large bank-year")
    print("\n" + "=" * 100)
    print("H5 (composition, BIG median-split contemporaneous size, same style as original H5-on-CI code)")
    print(f"  interaction beta={r2['coef']:+.9f}  CR2-Satt p={r2['p_CR2']:.6f}  df={r2['df_CR2']:.4f}  wild-cluster p={wp2:.6f}")
    print(f"  slope | small: beta={small['coef']:+.9f}  CR2-Satt p={small['p_CR2']:.6f}")
    print(f"  slope | large: beta={large['coef']:+.9f}  CR2-Satt p={large['p_CR2']:.6f}")
    print(f"  N={fit2['cov']['n']}  G={fit2['cov']['G']}")

    # --- 3. H5-on-composition: size classified at a FIXED base year (2020), matching
    # the original code's BIG_fixed_2015 robustness style but anchored on the same
    # Post2020 regime-split year used in H2, instead of within-sample contemporaneous size.
    base_year = 2020
    d3, x3 = iv._prepare(comp, "SW_stock", "AssetCostShare_raw", with_branch=False)
    base_lnta = d3.loc[d3["year"] == base_year, [idc, "lnTA"]].dropna().set_index(idc)["lnTA"]
    thr_base = base_lnta.median()
    big_base_map = (base_lnta > thr_base).astype(int).to_dict()
    d3["BIG_2020"] = d3[idc].map(big_base_map)
    n_before = len(d3)
    d3 = d3.dropna(subset=["BIG_2020"]).copy()
    d3["BIG_2020"] = d3["BIG_2020"].astype(int)
    d3["z_X_x_BIG2020"] = d3["z_X"] * d3["BIG_2020"]
    x3c = x3 + ["BIG_2020", "z_X_x_BIG2020"]
    fit3 = fit_generic(d3, "AssetCostShare_raw", x3c)
    r3 = contrast_report(fit3, {"z_X_x_BIG2020": 1.0}, "H5 BIG_2020 (fixed base-year size): SW_stock x BIG_2020 -> AssetCostShare_raw")
    wp3 = wild_p_for_contrast(fit3, {"z_X_x_BIG2020": 1.0})
    small3 = contrast_report(fit3, {"z_X": 1.0}, "slope | small-in-2020 bank")
    large3 = contrast_report(fit3, {"z_X": 1.0, "z_X_x_BIG2020": 1.0}, "slope | large-in-2020 bank")
    n_banks_base = base_lnta.shape[0]
    print("\n" + "=" * 100)
    print(f"H5 (composition, size FIXED at base year {base_year}, median lnTA={thr_base:.4f} across {n_banks_base} banks with a {base_year} observation)")
    print(f"  rows dropped for missing {base_year} size class: {n_before - len(d3)} of {n_before}")
    print(f"  interaction beta={r3['coef']:+.9f}  CR2-Satt p={r3['p_CR2']:.6f}  df={r3['df_CR2']:.4f}  wild-cluster p={wp3:.6f}")
    print(f"  slope | small-in-{base_year}: beta={small3['coef']:+.9f}  CR2-Satt p={small3['p_CR2']:.6f}")
    print(f"  slope | large-in-{base_year}: beta={large3['coef']:+.9f}  CR2-Satt p={large3['p_CR2']:.6f}")
    print(f"  N={fit3['cov']['n']}  G={fit3['cov']['G']}")

    # --- 4. TEMPORAL stability of H4 itself: SW_stock x Post2020 -> AssetCostShare_raw.
    # Not a size-moderation test. Year FE already absorb the Post2020 main effect,
    # so only the interaction term is added to the primary H4 spec.
    d4, x4 = iv._prepare(comp, "SW_stock", "AssetCostShare_raw", with_branch=False)
    d4["Post2020"] = (d4["year"] >= 2020).astype(int)
    d4["z_X_x_Post2020"] = d4["z_X"] * d4["Post2020"]
    x4c = x4 + ["z_X_x_Post2020"]
    fit4 = fit_generic(d4, "AssetCostShare_raw", x4c)
    r4 = contrast_report(fit4, {"z_X_x_Post2020": 1.0}, "H4 temporal: SW_stock x Post2020 -> AssetCostShare_raw")
    wp4 = wild_p_for_contrast(fit4, {"z_X_x_Post2020": 1.0})
    pre = contrast_report(fit4, {"z_X": 1.0}, "H4 slope | pre-2020 (beta1)")
    post = contrast_report(fit4, {"z_X": 1.0, "z_X_x_Post2020": 1.0}, "H4 slope | post-2020 (beta1+beta2)")
    n_pre = int((d4["Post2020"] == 0).sum()); n_post = int((d4["Post2020"] == 1).sum())
    print("\n" + "=" * 100)
    print("H4 TEMPORAL STABILITY: is SW_stock -> AssetCostShare the same pre/post 2020?")
    print(f"  rows: pre-2020={n_pre}, post-2020={n_post}")
    print(f"  interaction (beta2) beta={r4['coef']:+.9f}  CR2-Satt p={r4['p_CR2']:.6f}  df={r4['df_CR2']:.4f}  wild-cluster p={wp4:.6f}")
    print(f"  slope pre-2020  (beta1)      : beta={pre['coef']:+.9f}  CR2-Satt p={pre['p_CR2']:.6f}")
    print(f"  slope post-2020 (beta1+beta2): beta={post['coef']:+.9f}  CR2-Satt p={post['p_CR2']:.6f}")
    print(f"  N={fit4['cov']['n']}  G={fit4['cov']['G']}")

    # --- 5. Cutpoint-choice robustness: is "no temporal heterogeneity in H4" specific
    # to 2020, or does it hold for neighboring break years too? Guards against picking
    # 2020 because it happens to maximize significance (HARKing / cutpoint search).
    print("\n" + "=" * 100)
    print("CUTPOINT ROBUSTNESS: same test with alternative break years (2019/2021/2022)")
    alt_rows = []
    for yr in [2019, 2020, 2021, 2022]:
        da, xa = iv._prepare(comp, "SW_stock", "AssetCostShare_raw", with_branch=False)
        da["Post"] = (da["year"] >= yr).astype(int)
        da["z_X_x_Post"] = da["z_X"] * da["Post"]
        fita = fit_generic(da, "AssetCostShare_raw", xa + ["z_X_x_Post"])
        ra = contrast_report(fita, {"z_X_x_Post": 1.0}, f"interaction @ break={yr}")
        n_pre_a = int((da["Post"] == 0).sum()); n_post_a = int((da["Post"] == 1).sum())
        print(f"  break={yr}: n_pre={n_pre_a:3d} n_post={n_post_a:3d}  beta2={ra['coef']:+.6f}  CR2-Satt p={ra['p_CR2']:.6f}")
        alt_rows.append({"break_year": yr, **ra, "n_pre": n_pre_a, "n_post": n_post_a})
    pd.DataFrame(alt_rows).to_csv(Path(__file__).resolve().parent / "h4_temporal_cutpoint_robustness.csv", index=False)

    out = pd.DataFrame([
        {**r0, "wild_p": np.nan, "N": fit0["cov"]["n"], "G": fit0["cov"]["G"]},
        {**r1, "wild_p": wp1, "N": fit1["cov"]["n"], "G": fit1["cov"]["G"]},
        {**r2, "wild_p": wp2, "N": fit2["cov"]["n"], "G": fit2["cov"]["G"]},
        {**small, "wild_p": np.nan, "N": fit2["cov"]["n"], "G": fit2["cov"]["G"]},
        {**large, "wild_p": np.nan, "N": fit2["cov"]["n"], "G": fit2["cov"]["G"]},
        {**r3, "wild_p": wp3, "N": fit3["cov"]["n"], "G": fit3["cov"]["G"]},
        {**small3, "wild_p": np.nan, "N": fit3["cov"]["n"], "G": fit3["cov"]["G"]},
        {**large3, "wild_p": np.nan, "N": fit3["cov"]["n"], "G": fit3["cov"]["G"]},
        {**r4, "wild_p": wp4, "N": fit4["cov"]["n"], "G": fit4["cov"]["G"]},
        {**pre, "wild_p": np.nan, "N": fit4["cov"]["n"], "G": fit4["cov"]["G"]},
        {**post, "wild_p": np.nan, "N": fit4["cov"]["n"], "G": fit4["cov"]["G"]},
    ])
    out_path = Path(__file__).resolve().parent / "h5_composition_feasibility_results.csv"
    out.to_csv(out_path, index=False)
    print("\nSaved:", out_path)


if __name__ == "__main__":
    main()
