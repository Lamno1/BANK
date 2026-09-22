# Exogenous variation search — full log (ERA causal-gate exploration)

## Mandate

Under the ERA (End-to-End Research Agent) authorization, the causal gate was opened for autonomous exploration ("ERA toàn quyền tự quyết định mở causal gate khi thấy đủ căn cứ"). This log records a systematic search for a source of exogenous/quasi-experimental variation in bank-level software investment for the Vietnamese commercial banking panel (26 privately controlled banks, 2015-2025), conducted before deciding whether to reopen the causal design.

## Stopping rule (set retroactively, documented for transparency)

Six candidates were evaluated across two rounds. Each was checked against two criteria: (a) does it create cross-sectional variation in timing/exposure across the banks in this specific panel, and (b) is assignment to that variation plausibly independent of the bank characteristics that already confound the associational result (size, financial strength/CAMELS rating, management ambition). A candidate fails if it cannot satisfy both. The search stopped after six candidates because all six failed via one of three recurring, structurally consistent mechanisms (see Synthesis), indicating the pattern is a property of the institutional environment, not a lack of search effort.

## Candidates examined

### 1. Basel II pilot program (Circular 1601/2014/NHNN-TTGSNH, effective Feb 2016)
- **What it is:** SBV selected 10 banks for early Basel II piloting: Vietcombank, VietinBank, BIDV (all SOE, outside this study's SOE==0 panel), MB, Sacombank, Techcombank, ACB, VPBank, VIB, Maritime Bank (MSB). The remaining private banks in the panel faced a later mandatory deadline (~2020).
- **Why it looked promising:** Three of the pilot banks in this panel (TCB, VPB, MBB) are exactly the banks repeatedly identified as CR2-variance-dominant clusters throughout the ERA robustness work, suggesting a possible common regulatory driver of their elevated software investment.
- **Verification:** Official selection criteria (per SBV circular summaries) were: (i) the bank's own level of interest and readiness ("mức độ quan tâm và sẵn sàng của ngân hàng" — i.e., partly self-nominated), (ii) ensuring diversity of size and ownership type, (iii) scale relative to the system.
- **Verdict: REJECTED.** Selection is explicitly self-selected/negotiated ("interest and readiness"), not a deterministic rule. This is a more severe identification problem than simple size-based selection — a bank's willingness to volunteer for early regulatory compliance is itself correlated with the same unobserved management ambition/quality that plausibly drives software investment.
- Sources: [Basel II thí điểm 10 ngân hàng](https://kisvn.vn/17-ngan-hang-trien-khai-som-basel-ii-nhung-ai-da-ve-dich/), [tiêu chí lựa chọn](https://tapchikinhtetaichinh.vn/thuc-tien-ap-dung-tieu-chuan-basel-ii-tai-cac-ngan-hang-thuong-mai-viet-nam-43885.html)

### 2. Compulsory bank transfers ("chuyển giao bắt buộc")
- **What it is:** SBV forced distressed banks onto stronger acquirers at specific dates: OceanBank -> MB (Oct 17, 2024), CBBank -> Vietcombank (SOE, outside panel), GPBank -> VPBank, DongABank -> HDBank.
- **Why it looked promising:** Sharp, dated, externally imposed event on the acquiring bank; already investigated in this session as part of verifying MBB's 2025 asset-growth outlier.
- **Verdict: REJECTED.** Only 3 treated banks in the private panel (MB, VPB, HDB) — too few for a powered design. More fundamentally, SBV selects acquirers precisely because they are large and financially strong, which is the same selection-on-strength problem as candidate 1.

### 3. Circular 09/2020/TT-NHNN (information-system security in banking, effective Jan 1, 2021)
- **What it is:** Minimum information-security requirements (IT asset management, access control, incident management, business continuity, etc.), replacing Circular 18/2018.
- **Verdict: REJECTED.** Applies uniformly to all credit institutions on the same effective date. No cross-sectional variation in timing or exposure across banks in the panel; equivalent in structure to the Post-2020 dummy already used in the locked design.
- Source: [Thông tư 09/2020/TT-NHNN](https://thuvienphapluat.vn/van-ban/Tien-te-Ngan-hang/Thong-tu-09-2020-TT-NHNN-an-toan-he-thong-thong-tin-trong-hoat-dong-ngan-hang-455885.aspx)

### 4. Decree 85/2016/ND-CP (information-system security classification levels, 5 tiers)
- **What it is:** A government-wide classification scheme (not banking-specific) assigning information systems to security levels 1-5 based on criteria including user-base size (e.g., Level 3 threshold: an online service processing personal data for >=10,000 users).
- **Why it looked promising:** A formally defined numeric threshold, potentially usable for a regression-discontinuity design around the cutoff.
- **Verdict: REJECTED.** The threshold (10,000 users) is far below the actual scale of every bank in this 26-bank panel of established commercial banks; there is no bunching or cross-sectional variation around this cutoff within the sample — all banks are classified well above it, so the discontinuity does not bind.
- Source: [Nghị định 85/2016/NĐ-CP](https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Nghi-dinh-85-2016-ND-CP-bao-dam-an-toan-he-thong-thong-tin-theo-cap-do-317475.aspx)

### 5. Annual credit-growth quota ("room tín dụng")
- **What it is:** SBV allocates a maximum annual credit-growth ceiling to each bank, varying by bank and by year.
- **Why it looked promising:** Genuine bank-year-level cross-sectional and time variation, in principle usable as a shift-share/Bartik-style instrument.
- **Verdict: REJECTED.** Quota allocation is explicitly based on the bank's CAMELS rating (capital adequacy, asset quality, management, earnings, liquidity, sensitivity) — a composite health score that is directly and severely endogenous to almost every outcome of interest, including plausibly the bank's capacity and inclination to invest in technology. This is a more direct violation of exogeneity than any other candidate examined.
- Source: [Room tín dụng phân bổ theo CAMELS](https://www.dsc.com.vn/kien-thuc/room-tin-dung-trong-linh-vuc-ngan-hang-la-gi-nhu-the-nao-la-tot)

### 6. Stock-exchange listing timing (IPO / UPCOM-to-HOSE transfer)
- **What it is:** Banks in the panel listed or transferred exchanges at very different times: VPB (2017), TPB (2018), OCB and MSB (2020), SSB (2021), VAB (2025), KLB and VBB (2026), with ABB and BVB still on UPCOM as of the search date.
- **Why it looked promising:** Wide, genuine staggering across many years — structurally the richest timing variation found in this search.
- **Verdict: REJECTED.** Listing timing is a voluntary strategic choice made by each bank's own management when they judge conditions favorable; it is plausibly driven by the same unobserved "modernization/growth ambition" factor that would independently predict higher software investment, making it a simultaneity/reverse-causality risk rather than an exogenous shock. Several of the later events are exchange transfers (UPCOM to HOSE) for already-public banks, not first-time IPOs, further weakening any claim of a comparable "shock" across cases.

## Synthesis: three recurring failure modes

1. **Nationwide-simultaneous policy** (Circular 09/2020, e-KYC, QR interoperability): no cross-sectional variation to exploit; equivalent to information already captured by the existing Post-2020 temporal dummy.
2. **Discretionary or health-based selection into treatment/timing** (Basel II pilot, compulsory transfers, credit-growth quota, listing timing): assignment correlates directly with the same unobserved bank quality/strategy that confounds the associational result.
3. **Threshold exists but does not bind in this sample** (Decree 85/2016 information-system tiers): the cutoff is far outside the range of scale variation present among the 26 banks studied.

All six candidates fail via one of these three mechanisms; no seventh candidate was identified that plausibly avoids all three. This is treated as a structural property of the Vietnamese banking regulatory environment for this topic and period, based on what is publicly documented, not as an exhaustive proof that no such source could ever exist.

## Decision

**Causal gate remains closed.** This is not a default-cautious non-decision; it follows a bounded, documented search that found no candidate satisfying both required conditions. Any future causal upgrade would require either (a) a regulatory or market event not identified in this search, or (b) primary data collection (e.g., project-level IT implementation timing, vendor-contract dates) that could support a different identification strategy — both are outside the scope of the current ERA data-exploration pass.

## Verification note

All factual claims above (circular numbers, effective dates, selection criteria, listing dates) are drawn from web search results gathered in this session and are subject to the general caveat that secondary Vietnamese-language financial press may contain imprecision; primary legal texts were not independently retrieved and read in full for every circular. This log itself has not been through independent verification and should be treated as a research-process record, not a certified legal analysis.
