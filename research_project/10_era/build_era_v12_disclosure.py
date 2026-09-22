from pathlib import Path
from docx import Document
from docx.text.paragraph import Paragraph
from docx.shared import Pt, Inches

BASE = Path(r"D:\BANK\research_project")
SRC = BASE / "07_manuscript_reconstruction" / "FINAL_SUBMISSION_CANDIDATE_SCENARIO_A_V11.docx"  # read-only baseline
OUT = BASE / "07_manuscript_reconstruction" / "FINAL_SUBMISSION_CANDIDATE_SCENARIO_A_V12.docx"  # merged, official candidate


def append_to(doc, anchor, addition):
    p = next(p for p in doc.paragraphs if anchor in p.text)
    if addition not in p.text:
        p.text = p.text + " " + addition
    return p


def insert_after(ref, text, bold_heading=False):
    p = ref._parent.add_paragraph()
    run = p.add_run(text)
    if bold_heading:
        run.bold = True
    ref._p.addnext(p._p)
    return Paragraph(p._p, ref._parent)


def add_table_after(ref_element, headers, rows, doc, col_widths_in=None):
    """ref_element: an XML element (paragraph._p or table._tbl) to insert directly after.
    col_widths_in: list of column widths in inches, must sum to <= 6.0 (usable page width)."""
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.style = 'Table Grid'
    tbl.autofit = False
    for i, h in enumerate(headers):
        tbl.rows[0].cells[i].text = h
    for r in rows:
        cells = tbl.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = str(v)
    if col_widths_in:
        for row in tbl.rows:
            for i, w in enumerate(col_widths_in):
                row.cells[i].width = Inches(w)
        for i, w in enumerate(col_widths_in):
            tbl.columns[i].width = Inches(w)
    ref_element.addnext(tbl._tbl)
    return tbl


def add_para_after(ref_element, parent, text, bold_heading=False):
    """ref_element: an XML element (paragraph._p or table._tbl) to insert directly after."""
    p = parent.add_paragraph()
    run = p.add_run(text)
    if bold_heading:
        run.bold = True
    ref_element.addnext(p._p)
    return p


def main():
    doc = Document(SRC)

    # --- 1. Abstract ---
    append_to(
        doc,
        "The coefficient remains positive in all 26 leave-one-bank-out fits, but omitting TCB",
        "An exploratory decomposition using previously unused software-amortization schedules "
        "(covering 25 of 26 bank clusters, panel-wide 2014-2025) finds that removing the mechanical "
        "software-depreciation component from AssetCost leaves a smaller but still-positive association "
        "(approximately 65% of the original coefficient magnitude); this residual association is corroborated "
        "by wild-cluster bootstrap (p<=0.006 in the full sample and in every leave-one-bank-out configuration) "
        "but is borderline under CR2-Satterthwaite (p=0.057-0.072). Cluster-level decomposition further shows "
        "that MBB, not TCB, is the single most CR2-variance-dominant cluster (71% of variance in the full "
        "sample, rising to 92% once TCB is removed); TCB acts as a secondary counterweight whose removal "
        "exposes MBB's pre-existing dominance rather than being itself the primary source of fragility. MBB's "
        "2025 asset growth (~43% year-on-year) is independently verified against external financial-analyst "
        "and press sources as a real, reported event, not a data error. These exploratory findings are reported "
        "as a supplementary robustness thread and have not been folded into the primary locked specification.",
    )

    # --- 2. Results section 6.2: extend the leave-one-out sentence ---
    append_to(
        doc,
        "In the specification without branch_den, standardized SW_stock is positively associated",
        "An exploratory decomposition (Table 14) that removes the panel-wide software-amortization "
        "component from AssetCost yields a smaller coefficient (0.012071 without branch_den; 0.011664 with "
        "branch_den), approximately 65% of the original magnitude, borderline under CR2-Satterthwaite "
        "(p=0.057 and p=0.072 respectively) but corroborated by wild-cluster bootstrap (p=0.006 and p=0.005). "
        "This is reported as a supplementary exploratory check, not a replacement for the locked primary "
        "specification.",
    )

    # New Results subsection with the comparison table -- insert BEFORE "6.3" heading,
    # i.e. right after the end of section 6.2's own content.
    p62_end = next(p for p in doc.paragraphs if p.text.startswith("The coefficient means approximately 1.8455 percentage points"))
    heading = insert_after(p62_end, "6.2b Exploratory software-amortization decomposition", bold_heading=True)
    body = insert_after(heading,
        "Using a previously unused source schedule (annual software-amortization expense by bank-year, "
        "covering 25 of 26 privately controlled bank clusters across 2014-2025), AssetCost is decomposed into "
        "a software-driven component and a residual (ex-software) component. This tests whether the primary "
        "SW_stock -> AssetCostShare association is partly mechanical (software stock predicting its own "
        "amortization, which is itself part of AssetCost) rather than a broader cost-reallocation signal. "
        "The residual association survives at roughly 65% of the original magnitude in both the with- and "
        "without-branch_den specifications, indicating the association is not purely mechanical, but its "
        "CR2-Satterthwaite significance is materially weaker than the locked primary result.")
    move_table_headers = ["Specification", "Coef.", "CR2 p", "df", "Wild p", "N", "G"]
    move_table_rows = [
        ["Original, no branch_den", "0.018455", "0.0313", "3.7885", "0.002", "270", "26"],
        ["Ex-software, no branch_den", "0.012071", "0.0575", "3.6743", "0.006", "261", "25"],
        ["Original, with branch_den", "0.018019", "0.0376", "4.0014", "0.006", "270", "26"],
        ["Ex-software, with branch_den", "0.011664", "0.0721", "3.8762", "0.005", "261", "25"],
    ]
    tbl1 = add_table_after(body._p, move_table_headers, move_table_rows, doc,
                            col_widths_in=[1.9, 0.85, 0.7, 0.65, 0.65, 0.6, 0.65])
    cap = add_para_after(tbl1._tbl, doc,
        "Table 14. Ex-software decomposition, compared to the locked primary and secondary specifications. "
        "All rows use the same locked estimation pipeline; only the outcome's numerator (AssetCost vs AssetCost "
        "minus software amortization) differs.")

    ex2_intro = add_para_after(cap._p, doc,
        "As a broader exploratory battery, the same ex-software substitution (removing the software-amortization "
        "line from the relevant outcome) was applied to H1, H2, H4a, and H5 (Table 15). H1 (CASA baseline) and "
        "the already-null H2 Flow baseline are materially unchanged. H5's two supported size-heterogeneity terms "
        "are also materially unchanged, ruling out a software-amortization artifact there. H2 Flow x Post-2020 "
        "is the one case that shifts: its coefficient grows by about 25% under the ex-software CI, but its "
        "CR2-Satterthwaite significance weakens (p=0.0217 to p=0.0754) as df falls from 7.18 to 4.17, while "
        "wild-cluster bootstrap is unchanged (p=0.002 both ways). Cluster-influence decomposition attributes "
        "this to VPB, whose share of CR2 variance rises from 48% to 68% once the outcome is redefined; VPB was "
        "one of the two banks with a directly hand-confirmed high software-amortization share from the original "
        "2018 calibration exercise (7.71% of phys). The panel-wide software-amortization series built for this "
        "decomposition shows this is not confined to those two hand-checked bank-years: averaged over "
        "2015-2025, MBB has the highest mean software-amortization share of phys in the entire panel (14.1%), "
        "ahead of TCB (12.3%) and above VPB (8.9%); MBB's share also rose sharply in recent years (8.5% in "
        "2015 to 23.5% in 2024). This means MBB's dominance of the primary H4 result (Discussion, below) should "
        "not be read as unrelated to software intensity: MBB is independently the most software-intensive bank "
        "in the panel by this measure, and its 2025 asset-growth event is a second, separately verified factor "
        "layered on top of that; this analysis cannot separate how much of MBB's CR2 influence is attributable "
        "to each. H4a's own divergence "
        "(CR2 optimistic relative to wild-cluster, driven by LPB's null-residual concentration rather than by "
        "TCB, MBB, or VPB) is a structurally distinct mechanism, summarized alongside these results for "
        "completeness. H3 (SW_stock -> CI, already not supported) remains not supported under CR2-Satterthwaite "
        "when the software-amortization line is removed from CI (p=0.313 to p=0.236), though its wild-cluster "
        "p-value moves from 0.086 to 0.033; this boundary movement in a null result does not change the "
        "qualitative conclusion under the pre-specified CR2-primary reference.")
    ex2_headers = ["Hypothesis / term", "Coef. (orig -> ex-sw)", "CR2 p (orig -> ex-sw)", "df (orig -> ex-sw)", "Wild p (orig -> ex-sw)"]
    ex2_rows = [
        ["H1 CASA -> CI", "0.001668 -> 0.001637", "0.0006 -> 0.0010", "18.06 -> 17.61", "0.002 -> 0.002"],
        ["H2 Flow baseline -> CI", "0.000373 -> 0.000348", "0.286 -> 0.392", "5.09 -> 4.48", "0.257 -> 0.376"],
        ["H2 Flow x Post-2020 -> CI", "-0.002387 -> -0.002982", "0.0217 -> 0.0754", "7.18 -> 4.17", "0.002 -> 0.002"],
        ["H3 SW_stock -> CI", "-0.000559 -> -0.000719", "0.313 -> 0.236", "3.73 -> 3.70", "0.086 -> 0.033"],
        ["H5 Stock x BIG_it -> CI", "-0.009724 -> -0.009543", "0.0406 -> 0.0393", "n/a", "0.006 -> 0.006"],
        ["H5 Stock x continuous lnTA -> CI", "-0.003151 -> -0.003308", "0.0091 -> 0.0112", "n/a", "0.006 -> 0.006"],
    ]
    tbl2 = add_table_after(ex2_intro._p, ex2_headers, ex2_rows, doc,
                            col_widths_in=[1.8, 1.15, 1.15, 1.0, 0.9])
    cap2 = add_para_after(tbl2._tbl, doc,
        "Table 15. Ex-software sensitivity battery across H1, H2, H3, and H5 (CI-based outcomes). H4 is "
        "reported separately in Table 14 and Table 16; H4a has no ex-software analog (its outcome does not "
        "involve AssetCost) and is discussed only in the main text (Discussion, Section 7.4).")

    ex3_intro = add_para_after(cap2._p, doc,
        "A further exploratory battery covers the SW_delta (flow) version of the primary composition test and "
        "the H4R-A absolute contrast (NonAsset/TA - AssetCost/TA), for both SW_stock and SW_delta (Table 16). "
        "The SW_delta composition result, already classified as inference-sensitive in the locked design "
        "(CR2 p=0.0104, wild p=0.148), weakens further under the ex-software outcome (coefficient falls to "
        "about 57% of its original size; CR2 p=0.0769, wild p=0.269), reinforcing that it should not be read as "
        "confirmatory. The H4R-A absolute contrast for SW_stock follows the same pattern as the primary H4 "
        "result (about 85% of the original magnitude survives; CR2 weakens from p=0.0397 to p=0.0950; wild-"
        "cluster remains significant, p=0.002 to p=0.007), consistent with the same underlying association. "
        "The SW_delta version of this contrast was already null (CR2 p=0.917) and remains null under the "
        "ex-software outcome (CR2 p=0.630).")
    ex3_headers = ["Hypothesis / term", "Coef. (orig -> ex-sw)", "CR2 p (orig -> ex-sw)", "Wild p (orig -> ex-sw)"]
    ex3_rows = [
        ["H4 SW_delta -> AssetCostShare", "0.009571 -> 0.005444", "0.0104 -> 0.0769", "0.148 -> 0.269"],
        ["H4R-A SW_stock -> NonAssetMinusAsset", "-0.000972 -> -0.000825", "0.0397 -> 0.0950", "0.002 -> 0.007"],
        ["H4R-A SW_delta -> NonAssetMinusAsset", "0.000035 -> 0.000169", "0.917 -> 0.630", "0.909 -> 0.666"],
    ]
    tbl3 = add_table_after(ex3_intro._p, ex3_headers, ex3_rows, doc,
                            col_widths_in=[2.3, 1.4, 1.2, 1.1])
    add_para_after(tbl3._tbl, doc,
        "Table 16. Ex-software sensitivity for the SW_delta composition test and the H4R-A absolute contrast.")

    # --- 3. Discussion: correct/extend the influence-sensitivity paragraph ---
    append_to(
        doc,
        "The primary composition association is influence-sensitive.",
        "Cluster-level decomposition of the CR2 variance shows that MBB, not TCB, is the single most "
        "influential cluster in the full sample (71% of total CR2 variance versus 11.6% for TCB); removing "
        "TCB does not introduce fragility on its own so much as remove MBB's main counterweight, "
        "concentrating variance in MBB to 92% and collapsing df to 2.38. Symmetrically, removing MBB instead "
        "leaves TCB at a similar 71.5% dominance with df essentially unchanged (3.71), confirming that the two "
        "banks are exchanging the same structural role rather than TCB being uniquely responsible. MBB's 2025 "
        "total-asset growth (~43% year-on-year in the locked panel) was cross-checked against an independent "
        "financial-analyst report and press coverage; the 2024 base figure matches an external analyst report "
        "exactly, and press sources independently describe MB Bank as the fastest-growing asset base among "
        "Vietnam's largest banks in 2025, attributing this to organic credit and funding-cost factors rather "
        "than the bank's separately documented compulsory acquisition of OceanBank (which is real but "
        "quantitatively too small, at officially reported deal-level assets, to account for most of the "
        "observed growth). MBB 2025 is therefore judged to be a genuine, externally corroborated, but "
        "structurally exceptional observation, not a data error. This asset-growth event is not the only "
        "software-related feature of MBB: the panel-wide software-amortization series (Section 6.2b) shows MBB "
        "has the highest average software-amortization share of phys in the entire panel (14.1% over "
        "2015-2025, above TCB's 12.3% and VPB's 8.9%), rising from 8.5% in 2015 to 23.5% in 2024. MBB's "
        "outsized CR2 influence is therefore consistent with genuine software intensity as well as with the "
        "2025 asset event; this analysis does not attempt to apportion its influence between the two.",
    )

    # --- 4. Limitations ---
    append_to(
        doc,
        "The wild-cluster result is corroborative rather than a post-hoc replacement",
        "An exploratory supplementary decomposition further indicates that approximately one third of the "
        "primary coefficient's magnitude is attributable to the mechanical inclusion of software amortization "
        "within AssetCost, and that CR2-Satterthwaite fragility is structurally driven more by MBB's variance "
        "dominance than by TCB specifically. This decomposition uses a software-amortization source covering "
        "25 of 26 bank clusters (VBB unavailable) and has not been through the same multi-round audit applied "
        "to the locked primary specification; it is reported here as a transparent supplementary finding, not "
        "as a revision of the locked result.",
    )

    # --- 5c. Exogenous-variation search disclosure (added to Conclusion, near the existing causal-upgrade sentence) ---
    append_to(
        doc,
        "Future causal work would require a defensible external source of exogenous variation; that is outside the current design.",
        "A supplementary search for such a source examined six candidates specific to Vietnamese banking regulation "
        "and markets in this period (the 2016 Basel II pilot cohort, compulsory bank transfers, the 2020 "
        "information-system-security circular, the national information-system classification thresholds, "
        "annual credit-growth quotas, and stock-exchange listing timing). All six were rejected: each either "
        "applied uniformly to all banks with no cross-sectional variation, assigned timing through a "
        "discretionary or bank-health-based process correlated with the same unobserved factors already "
        "confounding the associational result, or involved a threshold that does not bind within this sample's "
        "scale. This bounded, documented search (full log preserved in the research project archive) is why the causal gate remains "
        "closed; it is a considered negative finding, not an unexamined default.",
    )

    # --- 5. Conclusion ---
    append_to(
        doc,
        "The association is influence-sensitive: the coefficient remains positive in all leave-one-bank-out fits,",
        "A supplementary exploratory decomposition indicates roughly two-thirds of this association survives "
        "after removing the mechanical software-amortization component of AssetCost, and that its "
        "small-cluster fragility is structurally linked to MBB's variance dominance at least as much as to "
        "TCB. These exploratory results reinforce, rather than overturn, the associational and "
        "influence-sensitive characterization of the primary finding.",
    )

    # --- 5b. H5 robustness under ex-software CI, and H4a CR2/wild divergence mechanism ---
    append_to(
        doc,
        "In the primary estimation sample, the Pearson correlation between raw SW_stock and lnTA is 0.670",
        "An ex-software version of CI (aggregate cost intensity net of the software-amortization line) leaves "
        "the H5 interaction estimates essentially unchanged: Stock x BIG_it moves from -0.009724 to -0.009543 "
        "(CR2 p 0.0406 to 0.0393) and Stock x continuous lnTA moves from -0.003151 to -0.003308 (CR2 p 0.0091 "
        "to 0.0112), both with wild p=0.006 throughout. H5's size-heterogeneity finding is therefore not a "
        "software-amortization accounting artifact.",
    )
    append_to(
        doc,
        "Similarly, network outcomes are inference-sensitive, and branch changes may reflect consolidation",
        "Diagnosing this inference-sensitivity directly: cluster-level influence on the H4a coefficient is far "
        "more evenly distributed than in the primary H4 result (top cluster LPB at 37% of CR2 variance, versus "
        "MBB's 71% in H4), so H4a's fragility is not a single-cluster-domination story. Instead, the "
        "null-restricted wild-bootstrap residuals are heavily concentrated in one cluster (LPB, 31% of total "
        "null residual sum of squares, driven by two poorly fit early-year observations), which widens the "
        "empirical bootstrap distribution to roughly 1.8 times the CR2-Satterthwaite standard error. This is "
        "the reverse asymmetry from the primary result: for H4, CR2 was the fragile method and wild-cluster "
        "was stable; for H4a, CR2 (p=0.013) appears optimistic relative to the wider empirical wild-bootstrap "
        "null distribution (p=0.083). Under the same pre-specified CR2-primary/wild-corroboration hierarchy "
        "used throughout, H4a's CR2 significance should not be read as robust confirmation given this "
        "divergence, consistent with its existing INFERENCE-SENSITIVE classification.",
    )

    # --- 5d. Table 4 caption/footnote: this is the pre-ERA, TCB-only narrative attached directly
    # to the primary results table -- must be brought in line with the MBB correction applied elsewhere.
    append_to(
        doc,
        "This is supplementary corroboration, not a post-hoc change in the primary inference hierarchy; CR2-Satterthwaite remains primary, with the TCB-excluded df=2.377 caveat retained.",
        "Cluster-level decomposition (Section 6.2b; Discussion) further shows that MBB, not TCB, holds the "
        "largest share of CR2 variance (71% versus TCB's 11.6%) and is independently the most "
        "software-amortization-intensive bank in the panel (14.1% mean share of phys, above TCB's 12.3%); "
        "TCB's role is best read as a counterweight whose removal exposes MBB's pre-existing dominance, not as "
        "the primary source of the fragility on its own.",
    )

    # --- 5e. Table 3 (variable definitions): AssetCostShare row claims "panel-wide share is not
    # separately identified" -- this is now false given the ex-software panel-wide series built in 6.2b.
    t3 = next(t for t in doc.tables if [c.text.strip() for c in t.rows[0].cells] == ['Variable', 'Definition', 'Role'])
    for row in t3.rows:
        if row.cells[0].text.strip() == 'AssetCostShare':
            row.cells[1].text = (
                "AssetCost/OPEX; AssetCost is the broader Fiin Chi ve tai san aggregate, including fixed-asset "
                "depreciation and other asset-related costs. Software amortization is embedded in depreciation "
                "at least in some bank-years (confirmed directly in two sampled cases, 8.86% and 7.71% of phys). "
                "An exploratory panel-wide series (25 of 26 clusters, 2014-2025, independently sourced "
                "but not validated with the same multi-round rigor as the two hand-confirmed points) estimates a "
                "pooled bank-year average software-amortization share of phys of approximately 4.0% (SD 5.0%, "
                "N=311 bank-years), with substantial bank-level variation (e.g., MBB and TCB average well above "
                "10%); see Section 6.2b and Tables 14 to 16.")

    # --- 6. Hypothesis-and-evidence-hierarchy table: update H4 status cell.
    # Found by header content, not positional index, because the newly inserted
    # EX-1 table above shifts doc.tables[] ordering.
    t0 = next(t for t in doc.tables if [c.text.strip() for c in t.rows[0].cells] == ['Hypothesis', 'Outcome', 'Role', 'Final status'])
    for row in t0.rows:
        if row.cells[0].text.strip().startswith("H4 Stock") and row.cells[2].text.strip() == "PRIMARY":
            row.cells[3].text = ("Supported association; CR2 influence-sensitive (driven more by MBB's "
                                  "variance dominance than by TCB; MBB independently has the panel's highest "
                                  "mean software-amortization share, 14.1%, plus a separately verified 2025 "
                                  "asset-growth event -- contributions not separable); wild corroborated; "
                                  "~65% of magnitude survives ex-software decomposition (exploratory)")
        if row.cells[0].text.strip().startswith("H4a"):
            row.cells[3].text = ("Inference-sensitive: CR2 (p=0.013) likely optimistic given LPB's "
                                  "concentrated null-residual variance widening the wild-bootstrap null "
                                  "distribution to ~1.8x the CR2 SE; wild p=0.083 not significant (exploratory)")
        if row.cells[0].text.strip().startswith("H5 Stock x size"):
            row.cells[3].text = ("Selected contemporaneous heterogeneity; unchanged under ex-software CI "
                                  "(exploratory), ruling out a software-amortization accounting artifact")
        if row.cells[0].text.strip().startswith("H1 CASA baseline"):
            row.cells[3].text = "Supported association; unchanged under ex-software CI (exploratory)"
        if row.cells[0].text.strip().startswith("H2 Flow baseline"):
            row.cells[3].text = "Not supported; remains not supported under ex-software CI (exploratory)"
        if row.cells[0].text.strip().startswith("H2 Flow x Post-2020"):
            row.cells[3].text = ("Supported; not treatment. CR2 weakens under ex-software CI (p=0.0217 to "
                                  "0.0754, driven by VPB's rising CR2-variance share) but wild-cluster is "
                                  "unchanged (p=0.002) (exploratory)")
        if row.cells[0].text.strip().startswith("H3 Stock"):
            row.cells[3].text = ("Not supported at 5%; remains not supported under CR2 with ex-software CI "
                                  "(p=0.313 to 0.236), though wild-cluster crosses 5% (0.086 to 0.033) "
                                  "(exploratory)")

    doc.save(OUT)
    print("Saved:", OUT)


if __name__ == "__main__":
    main()
