# REVIEW_B - Volitility-Model (domain-reviewer, as-built pass)

STATUS: FINAL (2026-11-02). As-built check of every REVIEW_A ruling (R1-R21) and lead rulings R-1/R-2 against source on disk.
Method: READ-ONLY. This role has no Bash, so nothing was executed or hashed. Numeric claims are HAND-DERIVED and labelled as such.
Scope of the text judged (traceability): the files as read in this pass. synthetic.py was RE-READ after the flow-lead's hash-change
notice. The current text differs from the first read only in the docstring (lines 11-12, 18: R16 figures 0.1076 -> 0.107537 and
0.412 -> 0.411); code lines 45-168 are unchanged. Per flow-lead that file is synthetic.py 1414ff07. The other files are the hub-stated
bs_pricing 12deadc4, data_io 3f0a1939, surface af6a5f38; viz.py, main.py and selftest.py were not hash-stated to me. HUB ACTION: run
`selftest.py --hashes` and confirm these match. Until then, ORACLE 108/108 (run on synthetic 73ee05b0) and this review are not shown
to cover the same bytes. The synthetic change is docstring-only, so an ORACLE re-run is expected to be unchanged, but that is an
expectation and has not been checked.
Error class this method cannot catch: a defect that exists only in a code path I misread. The R-1 hand check names the query that
confirms it; each defect's "Exact fix" column states the check that would settle it.
Routing note: owner_lane is limited to BUILD-A/B/C for the FIX round, but D3, D4, D6, D9 and D10 are in selftest.py, which QA owns
(OWNERSHIP.md:26). QA is still in progress (hub fact), so the hub routes these to QA. They are not BUILD fix-round items.

---------------------------------------------------------------------------------------------------
## 1. Ruling-by-ruling (IMPLEMENTED / NOT IMPLEMENTED, with evidence)

| Ruling | Kind | As-built | Evidence |
|---|---|---|---|
| R1 forward/parity | ACCEPT | IMPLEMENTED | data_io.py:84 F = S*exp((r-q)T), single definition; surface.py:179-180 k = ln(K/F) |
| R2 q range guard | CHANGE BUILD-B | IMPLEMENTED | data_io.py:263 Q_MAX=0.25; :266-282 _choose_q (trailing in [0,0.25], else dividendYield/100 in [0,0.25], else 0.0); :324-325 chosen q returned in MarketParams. Self-check :430-434 has cases that flip if the guard is removed. Stale docstring: see D8 |
| R3 console params + ticker note | CHANGE BUILD-C | IMPLEMENTED WITH EXCEPTION | main.py:133 exact `params: S=%.4f r=%.4f q=%.4f (continuous, decimal)`; main.py:36-38 ticker note matches R3 text character for character; :134-135 ticker-only. Exception D7: not always the first console item. No selftest asserts it |
| R4 OTM split at forward | ACCEPT | IMPLEMENTED | surface.py:42, :180-183 (k >= 0 -> call); selftest.py:327-341 |
| R5 | SUPERSEDED by R-1 | n/a | see R-1/R-2 below |
| R6 direct put, no parity, no 1-N | CHANGE BUILD-A | IMPLEMENTED | bs_pricing.py:105-106 call = dS*ndtr(d1) - dK*ndtr(d2); put = dK*ndtr(-d2) - dS*ndtr(-d1). Grep over all six source files: ndtr appears ONLY at these two lines, with signed arguments; no norm.cdf, no `1 - N`. No put anywhere is formed from a call. No test discriminates R6 (D9) |
| R7 status codes/bounds | ACCEPT | IMPLEMENTED | bs_pricing.py:33-41, :191-196 (order 4 -> 2 -> solve) |
| R8 total variance, W_FLOOR | ACCEPT | IMPLEMENTED | surface.py:40, :87, :58-66 |
| R9 k_lo/k_hi/in_domain | CHANGE BUILD-B | IMPLEMENTED | surface.py:116-118 fields; :346-349 k_lo = np.interp(T_grid, T_m, kmin_m), k_hi likewise, in_domain = k_lo<=k<=k_hi, from groups AFTER the thin-maturity drop (:312-323), as R9 requires. selftest.py:639-648 re-derives it from quotes |
| R10 term_structure in_domain | CHANGE BUILD-B | IMPLEMENTED | surface.py:456 `(k >= surface.k_lo) & (k <= surface.k_hi)`; selftest.py:933-948 proves False is reachable (noisy chain, 0.8S, T=1/12); mutation selftest.py:1228 |
| R11 diagnostic scope + wording | CHANGE BUILD-B | IMPLEMENTED | surface.py:384 calendar pair mask; :393 butterfly triple mask; n_checked = mask sums :397-400; disclaimer :47-49 matches R11(c) exactly (concatenation checked); R11(d) wording :373-375. Keys/line formats unchanged :401-408 |
| R12 anti-vacuity + in-domain injection | CHANGE QA | IMPLEMENTED (selftest.py as on disk) | selftest.py:809-820 n_checked >= 0.25*(n_T-1)*n_k and 0.25*n_T*(n_k-2), both methods; :833-845 single injection at an in-domain pair, asserts exactly 1 counted and locates the violating node independently == injected (i,j); :846-854 out-of-domain injection must NOT count |
| R13 term-structure gaps | CHANGE BUILD-C | IMPLEMENTED, UNTESTED | viz.py:219 y = NaN where in_domain False (taken from term_structure, not recomputed). No selftest exercises it (D4) |
| R14 3D hover domain tag | CHANGE, DEFERRED (R-3) | NOT IMPLEMENTED, OPEN EXCEPTION | viz.py:41-42, :57-70 customdata still 5 fields, no domain_tag. See OX-1. NOT closed |
| R15 same scaler in _w_fn | ACCEPT + check | IMPLEMENTED | surface.py:247-256: t0,ts,k0,ks are frozen from the usable quotes and the SAME closure scales the fit (:252) and every evaluation (:256); :339-341 grid and evaluate both go through w_fn (:138). rbf has no clamp (:336) |
| R16 truth arbitrage-free text | CHANGE BUILD-A (text) | IMPLEMENTED | synthetic.py:11-22 (current text, figures replaced by computed values per flow-lead). Hand re-check: 0.107537*1.5*1.7 = 0.2742 < 4; 0.107537*2.25*1.7 = 0.4113 <= 4; 4/(2.25*1.7) = 1.0458; (1/0.49)(1+sqrt(0.51))*1.5 = 5.247. All correct |
| R17 units | ACCEPT | IMPLEMENTED | viz.py:126, :139 percent only at display |
| R18 ACT/365 | ACCEPT | IMPLEMENTED | data_io.py:142, :339 |
| R19 cdn default | ACCEPT | IMPLEMENTED | viz.py:230; main.py:176 |
| R20 butterfly proxy | ACCEPT | IMPLEMENTED | surface.py:389-394 (non-uniform K row slopes). Vertical-spread bound still unchecked: accepted gap for README (OX-4) |
| R21 keep union, no tuning | CHANGE BUILD-B | IMPLEMENTED | surface.py:41 default "union"; not a CLI flag (main.py:55-82 has none); R21(3) asserted at selftest.py:877-878; R21(4) recorded in BUILD-B run-log (processed/pipeline-builder-BUILD-B__20261102131103.md line 10: "56 extrapolated-node butterfly violations, excluded by R11 scope") |
| R-1 vol-space acceptance | LEAD | IMPLEMENTED | bs_pricing.py:43 _SIGMA_RES=1e-9; :226 conv = usable & |diff|<=tol & (|diff/vega|<=1e-9 or diff==0); Brent short-circuits only on an exact 0 at an endpoint :264-267 |
| R-2 vega guard, status 2 band | LEAD | IMPLEMENTED | bs_pricing.py:223-228 usable = vega >= 1e-8 (False for NaN); ~usable retired to Brent, safe denominator so no resid/vega division; :193 status 2 = p <= lower+1e-10 or p >= upper-1e-10, so a price in (1e-10, 1e-8] is solved, not out_of_bounds |

### R-1 hand check (deep-OTM put; HAND-DERIVED, 4-5 significant figures)
Row: S=100, r=0.04, q=0.015, T=1/12, K=70 put (clean chain).
- F = 100*exp(0.025/12) = 100.2086; k = ln(70/100.2086) = -0.35876.
- atm_vol = 0.18 + 0.06(1 - e^-0.08333) = 0.184797; theta = T*atm^2 = 0.0028458.
- phi*k = -0.53815; (phi*k + rho)^2 + 0.51 = 2.04300, sqrt = 1.42934; w = (theta/2)(1 + 0.37670 + 1.42934) = 0.0039928.
  sigma_true = sqrt(w/T) = 0.21889; sqrt(w) = 0.063189.
- d1 = (0.356675 + 0.0020833 + 0.0019964)/0.063189 = 5.7091; d2 = 5.6459.
- Mills-ratio tails: N(-d2) = 8.214e-9, N(-d1) = 5.678e-9. K e^-rT = 69.767, S e^-qT = 99.875.
  put = 5.7306e-7 - 5.6707e-7 = about 6.0e-9 (hand precision about +/-1e-10).
- The price sits in (1e-10, 1e-8]. It is NOT status 2 (R-2), and it is BELOW tol = 1e-8, so price-only acceptance would accept any sigma.
- Solver path as built: the Brenner-Subrahmanyam seed = sqrt(2*pi/T)*p/(S e^-qT), about 5e-10, is clipped to IV_MIN = 1e-4 (:201-202). At sigma=1e-4,
  |diff| = 6e-9 <= tol, so a PRICE-ONLY rule accepts iv = 1e-4 against a truth of 0.219, which is the false-converged marker. As built, vega at
  sigma=1e-4 is about 0 (d1 is about 1.2e4), which is < 1e-8, so the row is retired to Brent (:223, :228). Brent brackets: f(1e-4) = -6e-9 < 0, f(5) > 0,
  and brentq xtol 1e-12 returns sigma about 0.21889, status 1. Near the root, vega = S e^-qT phi(d1) sqrt(T) = 99.875*3.336e-8*0.2887 = 9.62e-7,
  which is >= 1e-8, so Newton is also allowed there and must meet |diff/vega| <= 1e-9.
- Cancellation (stated plainly): the direct put still subtracts two terms of about 5.7e-7 to leave 6e-9 (about 2 digits lost, about 14 kept).
  Parity would subtract terms of about 100 (the dS*N(d1) term dominates the rounding), losing about 10 digits. That is an absolute error of about 1e-14,
  or about 2e-8 in IV at this row (vega 9.6e-7). So the 1e-6 round trip would NOT catch a parity put here. R6 therefore rests on numerical practice and on reading, and
  no test enforces it (D9). Calibration note on my own REVIEW_A R6 rationale ("quietly fails the 1e-6 round-trip"): overstated for this row.
  At rows near BOUND_EPS the margin shrinks to within about 1 order of magnitude. The ruling stands; its stated consequence is weaker than written.
- Confirms fastest: `prepare_quotes(generate_chain(noise_bps=0,tick=0,min_price=0), mp)` row T=1/12, K=70: expect status 1 and |iv - sigma_true| < 1e-9.

---------------------------------------------------------------------------------------------------
## 2. New defects (green-marker hunt and as-built)

No defect changes a computed IV, surface value, or diagnostic count. ONE produces a wrong PRINTED number (D1, ticker path).

| ID | Sev | owner_lane | file:line | Defect | Exact fix |
|---|---|---|---|---|---|
| D1 | MINOR | BUILD-C | main.py:103, :108, :115, :137, :136 | Control total 1 as printed and asserted in main is a TAUTOLOGY: n_read is DEFINED as len(chain)+len(rejects) (csv) or len(chain) (ticker/synthetic), then :137 asserts that same sum. It cannot fail. The loader's independent counter chain.attrs["rows_read"] (data_io.py:252) is ignored. WRONG NUMBER: on --ticker the console prints "0 rejected" although fetch drops non-positive and duplicate rows (data_io.py:357-360) | csv: n_read = chain.attrs["rows_read"]. ticker: print "rows dropped by fetch: not reported (CONTRACT 5.3)" instead of "0 rejected". The real CT1 at data_io.py:245 stays |
| D2 | MINOR | BUILD-B | surface.py:211-214, :355-357 | CT2 "recomputed independently" reuses the same F/k arrays and expression as the split, and is GATED by `if OTM_CALL_AT_BOUNDARY`, so it is off exactly when the boundary flag it should police is flipped. CT3 counts the same mask twice, an identity. Both are mitigated by main.py:145-148 and :162-164 (separate path) | Remove the OTM_CALL_AT_BOUNDARY gate; recompute from chain columns with its own forward call; label CT3 as an identity or recount from the interpolator inputs |
| D3 | MINOR | QA | selftest.py:443 | Price-only acceptance comes back in a test: passes if |iv-sig| < 1e-4 OR price residual <= 1e-8. On a sub-1e-8 deep-OTM price the OR clause accepts any root, the exact failure R-1/R-2 forbid. Mitigated by selftest.py:279-285, and by mutation :1230 only IF QA's proof reports it RED (not seen by this lane). Open question for QA: with the R-2 vega guard, sub-1e-8 rows go to Brent from the seed whatever the price test says, so whether that mutation goes red depends on rows of intermediate vega. QA should report the result | Replace with: if status in {0,1}: assert |iv - sig| <= 1e-6 |
| D4 | MAJOR | QA | selftest.py:985-989, :1034-1038; MUTATION_TABLE :1214-1240 | R13 (a binding CHANGE) has NO failing check. c07 builds from the CLEAN chain, where 0.8S at T=1/12 (k = -0.225) is inside the quoted range (lowest usable put about 0.675S, k about -0.40), so no gap ever occurs. No mutation targets viz.py:219. If a gap did occur, :1038 `np.abs(ya-y1).max()` becomes NaN | Add a c07 check on the NOISY default chain: "Term K=80.00" y[0] is NaN and y is NaN exactly where term_structure(...).in_domain is False (count > 0). Add mutation: viz.py:219 np.where(...) -> 100.0*ts["iv"] must turn that check red. Use np.nanmax at :1038 |
| D5 | MINOR | BUILD-C | viz.py:90-91, :215, :223-226 | Labels claim more than the content: the docstrings say out-of-domain points "are drawn as 'x' markers", and hover shows "in quoted range (1=yes)". With y = NaN those points do not render, so neither the marker nor the hover can be seen | Reword: "out-of-domain points are omitted (gap in the line, R13)"; drop the dead symbol list or keep it with a comment that it is inert |
| D6 | MINOR | QA | selftest.py:918 | Stale failure message "in_domain flag != k_grid containment"; the check is now k_lo/k_hi (R10) | Message: "in_domain != k_lo<=k<=k_hi (R10)" |
| D7 | MINOR | BUILD-C (+QA) | main.py:98-99, :105-106 vs :133 | R3 says the params line is ALWAYS the first console item; the "--noise-bps/--seed ignored" note prints before it on --csv/--ticker. No selftest greps the params line | Print the params line before those notes (move the notes after :133). QA: assert so.splitlines()[0].startswith("params: S=") in c09 |
| D8 | MINOR | BUILD-B | data_io.py:290-291 | Stale docstring: "q is the trailing annual dividend yield as a DECIMAL (0.0 if absent)", which contradicts the R2 rule at :298-300 in the same docstring | Delete :290-291's q clause; keep :298-300 |
| D9 | MINOR | QA | selftest.py (c01, MUTATION_TABLE) | R6 has no discriminating test: the 1e-6 IV round trip cannot see a parity put (hand estimate above: about 2e-8 IV error). Only reading enforces it | Add: deep-OTM put relative price error vs ref_price (erfc-based, selftest.py:68-77) <= 1e-12 at S=100,K=70,T=1/12,r=.04,q=.015,sigma=0.21889; add mutation bs_pricing.py:106 -> `put = call - (dS - dK)` that must turn it red |
| D10 | MINOR | QA | selftest.py:1238 vs data_io.py:360, :214-216 | Mutation that reaches code no check runs: `loader_keeps_last_duplicate` rewrites keep="first", whose ONLY hit is data_io.py:360 (drop_duplicates inside fetch_yfinance_chain, never called by selftest). The CSV loader's duplicate rule is the `seen` set at :214-216, which no mutation touches. c11 cannot go red from this mutation: the proof either reports NOT CAUGHT or goes red for an unrelated reason | Mutate data_io.py:215 `if key in seen:` -> `if False:` and require c11_loader_quarantine_and_control_total red |
| D11 | MINOR (no fix) | BUILD-A | bs_pricing.py:281-282 | Self-test reference ncdf uses 0.5*(1+erf(x)), a 1-N style form, but only at d1=0.25/d2=0.05 (no tail). Not an R6 breach (R6 governs bs_price) | none required |

---------------------------------------------------------------------------------------------------
## 3. Exceptions reported, NOT absorbed

| ID | Status | Basis | Magnitude | Owner |
|---|---|---|---|---|
| OX-1 R14 3D hover/corner labelling | OPEN, DEFERRED by flow-lead R-3 | REVIEW_A R14; default R13 alone in force | Hand estimate from R9 figures, default noisy chain, T=1/12 row: quoted k about [-0.107, 0.093] of a union grid about [-0.56, 0.29], so about 24% in-domain and about 76% of that row extrapolated and unlabelled on the 3D surface | BUILD-C; HANDOFF names it in README limitations |
| OX-2 Smile panel extrapolation unlabelled | OPEN, NEW | OPINION (no ruling covers it); same presentation-materiality rationale as R13 | smile() spans the full union k_grid at every T (surface.py:424-435, viz.py:155-161); the T=1/12 smile is about 76% extrapolated (same hand estimate). The quote markers show where the data is, which partly mitigates | flow-lead to rule (CONTRACT 6.5/7.1); BUILD-C if adopted (NaN outside [k_lo(T), k_hi(T)] via np.interp, as R13) |
| OX-3 Noisy-chain in-domain butterfly counts | OPEN, REPORTED | REVIEW_A R15 opinion (tick rounding in wings) | Builder-reported, not derived here: rbf 1/3912, spline 8/3912 in-domain; calendar 0/3953 (source: team-memory/projects/Volitility-Model/inbox/processed/pipeline-builder-BUILD-B__20261102131006.md line 7) | v2 decision; README |
| OX-4 Vertical-spread bound unchecked | ACCEPTED GAP | REVIEW_A R20 | n/a | HANDOFF (README) |
| OX-5 R2 dividendYield-as-percent | RESIDUAL RISK | REVIEW_A R2 marked the percent claim UNVERIFIED recall; ticker path untested live | If Yahoo reports decimal there, the fallback gives q/100 (in range, so the guard does not reject it); mitigated by the R3 printed q | none in v1; README |

---------------------------------------------------------------------------------------------------
## 4. Disclosure / IP
None. Synthetic data only; no employer identifiers, account codes, or error magnitudes attributable to a named party. Control totals and
validation counts above are fine to share.

VERDICT: treatment CORRECT on every ruling (R14 open by deferral); no computed number wrong, one printed count wrong (D1); close D4 before R13 is claimed verified.

---------------------------------------------------------------------------------------------------
## 5. DELTA PASS 2026-11-02 (after the R-9 fix round; fresh REVIEW-B instance; READ-ONLY, no Bash)
Scope: the four flow-lead items (PAUSED_R9_TO_BLOCKS.md) plus the gaps found while reading them. Bytes judged: the hub-stated
hashes viz edc7196f, main 900228c8, selftest 34fbf338 (data_io 589f5c78 and surface be111b3e are comment-only per hub). I could
not hash anything myself. Execution results (38 checks, mutation proof, tick=0 report, live --ticker run) are HUB FACTS and are
cited as such, not re-observed. D2 and D8 were NOT re-read in this pass and are not claimed closed here.

| ID | Status | owner_lane | file:line | Finding |
|---|---|---|---|---|
| D4 | CLOSED, CONDITIONAL | QA | selftest.py:951-977, :1261-1264, :1301, :1338-1339, :134-141 | Check c06_r13_ox2_viz_gaps_where_out_of_domain_noisy_chain builds on the NOISY default chain (noisy_setup :134-141, `syn.generate_chain()` defaults). It asserts that the term-trace NaN pattern equals ~in_domain (:966) and that the smile NaN pattern at T=1/12 equals ~in_domain[0] (:977). Out-of-domain points are guaranteed: (~dom).any() at :965 (term), (~domrow).any() at :976 (smile), and the independent quote-extent check k0 < kmin for 0.8S at T=1/12 at :943. Scratch mutations: `viz_term_nan_mask_removed` (:1261-1262) and `viz_smile_nan_mask_removed` (:1263-1264). Each rewrites the np.where mask to the unmasked 100*iv in a TEMP COPY (copy_tree :1280-1285, tempfile.mkdtemp :1302). Live-hash assertion: before at :1301, after plus ensure at :1338-1339 (SOURCES only, which are the only files mutated). Hub reports both RED. CONDITION: see D12. The proof's RED cannot be attributed until the hub quotes the line `BASELINE copy: rc=0 failed=[]` from the same run. Sub-item "use np.nanmax at old :1038" (now :1067) was NOT applied. This is harmless, because a NaN makes `> 1e-2` False and the check fails closed (a false red, never a false green) |
| OX-2 | CLOSED (as ruled by R-9), with D13 | BUILD-C | viz.py:158-165 | Smile line y = NaN outside the domain; trace names unchanged. Asserted by :977 and mutation :1263 |
| D5 | CLOSED | BUILD-C | viz.py:91-92, :224, :226-228 | The text now says "NaN, rendered as a gap in the line (R13)" and "the same gap rule applies to the smile lines (OX-2)". The only `symbol` left is the market-quote diamond at :174, which is a real rendered marker. The dead "in quoted range (1=yes)" hover field is gone (term hover :234 shows T, IV, k only) |
| D1 | CLOSED | BUILD-C | main.py:110, :126-130, :154-157, :159, :161 | CSV: n_read is a raw non-blank line count minus the header, taken by its own file read (:126-130) and independent of the loader, and kept + rejected come from the loader. The assert at :156 can now fail. Ticker prints "rejected: n/a, ticker fetch drops rows silently" (:159). Synthetic prints "rejected: n/a" (:161). No made-up 0. OPINION (no fix required in v1): a quoted CSV field with an embedded newline would make :156 fail on a valid file, which is a false red, the safe direction. The control is also an `assert`, so it disappears under `python -O` |
| D7 | CODE CLOSED / TEST OPEN | BUILD-C (code), QA (test) | main.py:147-152; selftest.py (none) | The params line now prints immediately after _acquire_chain (:148), before the ticker note (:150) and the ignored-flag notes (:151-152, built at :106/:114). data_io.py prints nothing on the fetch path (its only print is the self-check, :445). The QA half from section 2 is NOT present: a Grep of selftest.py for `params:` returns nothing. So R3 ordering has no check that can fail. The hub's live observation is a run, not a test. MINOR. Fix: in c09, assert `out.splitlines()[0].startswith("params: S=")` for the synthetic and --csv-with-noise-flag paths, plus a mutation that moves :148 below :152 |
| D3 | CLOSED | QA | selftest.py:442-445 | The price-only clause is gone. If status is in {0,1}, |iv - sig| <= 1e-6 is required. Otherwise iv must be NaN. The R-1/R-2 interaction is reported correctly as the INFO mutation `iv_price_only_alone_vega_guard_masks` (:1271-1272) plus the pair mutation `iv_price_only_and_no_vega_guard` (:1273-1276, RED per hub). That matches section 2's open question: the vega guard is defense in depth, and it masks the single mutation |
| D6 | CLOSED | QA | selftest.py:917 | Message: "in_domain flag != R10 rule k_lo[i] <= k_i <= k_hi[i]" |
| D10 | CLOSED | QA | selftest.py:1269-1270 | Now mutates the CSV loader's `if key in seen:` (the rule c11 exercises), not the fetch-path keep= argument. RED per hub |
| D12 NEW | OPEN | QA | selftest.py:1308-1309, :1330-1332 | The mutation proof's attribution can be vacuous. `hit` is taken from `failed` (:1331), not from `new_red` (:1330). The baseline rc0/failed0 is printed (:1309) but never asserted. If the baseline copy already failed a must_fail check, every mutation listing that check would print "RED as required" without the mutation having caused anything (LESSONS: a gate that has never been red because of the change is not evidence). MINOR, because the hub's live selftest is 38/38 green on the same bytes, so the baseline is expected to be clean. Fix: `ensure(rc0 == 0 and not failed0, ...)` after :1309, and `hit = [c for c in must_fail if c in new_red]` |
| D13 NEW | OPEN | BUILD-C | viz.py:159-162 | The smile domain comes from the NEAREST GRID ROW, not the slice. Smiles are evaluated at the exact quoted T (surface.py:442), but the mask is in_domain[argmin|T_grid - T|]. That is a second definition of the domain, which diverges from R9 off the grid (LESSONS: state every relation once). HAND-DERIVED for the defaults: T_grid = linspace(1/12, 2, 60), dT = 0.032486. n_smiles=5 over 8 maturities picks indices 0,2,4,5,7, so T = 1/12, 3/12, 9/12, 1.0, 2.0. Of these, 1/12 and 2.0 are exact rows. 3/12 maps to row 5 (T=0.24576) and 1.0 maps to row 28 (T=0.99294). Both lean toward the SHORTER neighbour, which has the narrower domain (assumed: on a fixed strike set the quoted k range widens with T), so the error direction hides data and is safe. 9/12 maps to row 21 (T=0.76554), 6.2% of the way toward 1.0, which has the WIDER domain. That is the R13-forbidden direction: an extrapolated node can be drawn as data. Estimated magnitude: 0.062 x (edge gap 9/12 to 1.0), well under one k node (k spacing about 0.0108), so 0 or 1 node per edge. The check at :975 tests only row 0, where the mapping is exact, so it cannot see this. Basis: R9 per-slice domain. Severity MINOR, OPINION on materiality. Fix: at a quoted T use the slice's own quotes, `kq = qk[np.isclose(qT, T)]` (already formed at :171), and `dom = (k_grid >= kq.min()) & (k_grid <= kq.max())`. QA should then assert at T=9/12 |
| OX-3 | OPEN (v2 / README) | v2 decision | n/a | QA's tick=0 report (hub fact): in-domain butterfly goes from rbf 1/3912 and spline 8/3912 to 0/3871 for both. This SUPPORTS tick rounding as the cause, but the comparison is not like-for-like, because n_checked changed (3912 to 3871: the tick=0 chain changes which quotes survive min_price, and so the domain). README: say the counts are small, are attributed to tick rounding in the wings, and that the attribution is supported by a tick=0 run with a different denominator |
| OX-5 | OBSERVED ONCE, NOT VERIFIED | none in v1; README | data_io.py (R2 fallback) | The hub's live --ticker run gave q = 0.0075, which is in [0, Q_MAX=0.25]. That cannot settle OX-5. The residual risk is that a field already in DECIMAL gets divided by 100, and the result of that also lands inside [0, 0.25], so being in range is consistent with either units hypothesis. The observed value is about 100x above where the failure value for an ordinary equity yield would sit, but which branch produced q (trailing yield or dividendYield/100) was not reported, and the percent-unit claim for dividendYield is still UNVERIFIED recall (REVIEW_A R2). Mark it "observed on one ticker, 2026-11-02; branch not reported". To close it, print the chosen branch and the raw field values in the params note, or have the hub report them from the same fetch |
| OX-1, OX-4 | UNCHANGED | BUILD-C / HANDOFF | see section 3 | R14 still deferred (R-3). Vertical-spread bound still unchecked |

### README wording for real-chain diagnostic counts (ruling for HANDOFF; basis R11(c) disclaimer, R20, CONTRACT no pass/ok keys)
- Present them as dated, single-ticker DIAGNOSTICS on raw mid quotes. Always show violations / n_checked with the denominator, the method,
  the run date and the scope "in-domain nodes only". No pass/fail, ok or green wording, and no thresholds.
- Name the expected sources plainly: bid/ask noise in mids, AMERICAN options priced with a EUROPEAN model (early-exercise premium,
  mostly puts), discrete dividends against a continuous q, stale or non-synchronous quotes, and interpolation between sparse slices.
- State that the counts are NOT arbitrage opportunities and NOT evidence that the fit failed. Live data changes, so the counts are not reproducible.
- Do NOT put them next to the near-zero synthetic counts as a quality comparison. The synthetic counts test the code; the real
  counts describe one day's data. Hub-reported shares for that one run: calendar 575/2831 (about 20%), butterfly 174/2793 (about 6%).

### Disclosure / publication flag (raised proactively)
- R-10(d) puts TICKERS in the widened pre-push scan, and REVIEW_B.md is in case-study scope (U-D/U-E). The hub's smoke run names a
  public index ETF. It is not attributable to any party and the risk is low, but under R-10(e) a ticker hit HOLDS for the user. I have
  deliberately not written the ticker into this file. If HANDOFF writes it into README.md with the counts, the scan will hit it.
  The user decides whether to name it or use "a liquid US index ETF". Control totals and validation counts are fine to share.

DELTA VERDICT: no MAJOR open. D4 is closed on the condition that the hub quotes the mutation-proof `BASELINE copy: rc=0 failed=[]` line
(D12). New MINORs: D12 (QA) and D13 (BUILD-C). D7's test half is still open (QA). None of these changes a computed IV, surface value or
diagnostic count.
