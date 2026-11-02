# PAUSED - R-9 fix round, not yet delivered (hub transport file)

Paused for a user break on 2026-11-02. flow-lead issued ruling R-9, which is in the OWNERSHIP.md corrections log, before the pause. The TO blocks below are copied verbatim from flow-lead's output and NONE has been delivered yet.
The QA agent was stopped mid-edit on selftest.py. Its last words were "Now the other edits: round trip deep-OTM, in_domain independent, R10 false case, main disclaimer, notes printing." Treat selftest.py as possibly partially edited, and run it before relying on it.

Last known green (hub live run 2): main.py exit 0 (rbf and spline/strike), the 5 module self-checks exit 0, oracle 108/108, selftest 37/37.
Hashes: bs_pricing 12deadc4, synthetic 1414ff07, data_io 3f0a1939, surface af6a5f38, viz b352af85, main ac2ab824, selftest efd3db20.

## Resume order (from flow-lead TO HUB)
1. Re-run selftest.py and hash it, because QA was stopped mid-edit.
2. Resume QA so it finishes its current report.
3. Send TO BUILD-B and TO BUILD-C, in parallel.
4. When BUILD-C reports done, send TO QA.
5. Hub live run, and report the new hashes.
6. Send TO REVIEW-B (delta pass).
7. Then HANDOFF, then the flow-lead retro and the judge-rate restore, then a fresh memory-curator terminal pass.
8. Hub runs n+1 live runs, then pushes to github.com/nygiantsmax-rgb/Volsurface.

## R-9 summary
- **BUILD-C:** D1, D5, D7, OX-2 (apply R13 to the smile panel).
- **BUILD-B:** D2, D8.
- **QA:** D4 (MAJOR), D3, D6, D10.
- **Deferred:** D9; OX-1, OX-3, OX-4 and OX-5 become README exceptions.
- **No fix needed:** D11.

## TO BUILD-C
Fix round R-9. Edit only viz.py, main.py and requirements.txt. Write your run-log once, at the end.
1. D1: control total 1 in main.py (lines 103, 108, 115, 137) computes the count as the sum it asserts, so it cannot fail. On --ticker it prints "0 rejected" even though the fetch silently drops rows. Fix it so no printed count claims more than its source. If you can compare against an independently obtained total (rows returned by the loader against rows after filtering), do that and let the assertion fail on a mismatch. If you cannot, print the line without the rejected count, or as "rejected: n/a (ticker fetch drops rows silently)". Do not print a number that can't be wrong.
2. D5: the docstrings and hover in viz.py (lines 90-91, 215, 223-226) say out-of-domain points show as 'x' markers, but y=NaN renders as a gap. Correct the text to say gap. Describe only what renders.
3. D7: the params line from R3 must be the first line printed. The --noise-bps/--seed note currently comes before it at main.py:98-99 and 105-106. Move it after.
4. OX-2: apply the R13 principle to the smile panel. Out-of-domain points are y = NaN, never an extrapolated value, and trace names are unchanged. Use Surface.in_domain from the real surface. Prove it fires on the default noisy chain, T=1/12, and show the NaN indices equal the in_domain False indices. If you cannot land it this round, say so plainly in the run-log. Do not leave it half-done.
5. R14 stays deferred. Do not touch the hovertemplate or customdata.
6. Re-run main.py end to end for rbf and spline/strike, using PowerShell $LASTEXITCODE. Report the exit codes, the new viz.py hash, and "attestation: edited only viz.py, main.py and requirements.txt".
Message the hub when done, and QA is released on your done notice.

## TO BUILD-B
Fix round R-9. Edit only data_io.py and surface.py. Write your run-log once, at the end.
1. D2: surface.py lines 211-214 and 355-357. Control total 2 is switched off by the flag it polices, and control total 3 is an identity. Do not add logic. Change the comments or labels to say plainly that these are structural checks and that main's own recount is the gate. A check must not claim more than it does.
2. D8: the data_io.py docstring (lines 290-291) contradicts R2. Correct it to the R2 rule (trailingAnnualDividendYield in [0, 0.25], else dividendYield/100 in [0, 0.25], else 0.0). Leave the code unchanged.
3. Re-run both self-checks with `-W error`. Report the exit codes from PowerShell $LASTEXITCODE, the new file hashes, and "attestation: edited only data_io.py and surface.py". No signature changes.

## TO QA (send once QA's current report has landed and BUILD-C's done notice is in hand)
Fix round R-9. Edit only selftest.py. Write your run-log once, at the end.
1. D4, MAJOR: no check can currently fail on R13. The fixture is the clean chain, where no gap occurs, and no mutation targets viz.py:219. Fix:
 - Use the default noisy chain, T=1/12, K=0.8*S.
 - Assert that the term-structure trace y is NaN exactly where in_domain is False, with at least one NaN present (anti-vacuity).
 - Add a mutation on a SCRATCH copy of viz.py that removes the NaN masking. It must turn the check red.
 - Assert the live file hash is unchanged afterward.
 - Do the same for the smile panel (OX-2), once BUILD-C reports it landed.
2. D3: selftest.py:443 has an "OR price residual <= 1e-8" clause. It reintroduces the price-only acceptance that R-1 forbids. Remove the clause. The round-trip check is only |iv - sigma_true| <= 1e-6 over status in {0,1}.
3. D6: selftest.py:918 has a stale failure message. Correct it to match what the check asserts now.
4. D10: the duplicate-row mutation hits data_io.py:360 inside the yfinance fetch, which no check calls. Retarget it at the CSV loader's duplicate rule (data_io.py:214-216) on a scratch copy, so the check is mutated on a path the selftest actually runs. Show it go red.
5. Do not add a test for D9.
6. Report PASS/FAIL counts from the PowerShell exit code, the new selftest.py hash, and "attestation: edited only selftest.py".

## TO REVIEW-B (send after the fix round, with the new hashes)
Delta pass only. Do not redo the full review. You have no Bash.
Read the new viz.py and selftest.py. Check four things:
- D4 and OX-2: the R13 check in selftest.py can fail. Name the scratch mutation and where the live-hash assertion is, and confirm the noisy-chain fixture contains at least one out-of-domain point.
- D5: the viz.py text now says "gap", not "x markers".
- D1 and D7: the main.py control total and the params line are fixed as described.
- D3: the price-only clause is gone at selftest.py:443.
Add a short dated section at the end of REVIEW_B.md with findings carrying owner_lane and file:line. Attest "edited only .claude/REVIEW_B.md". Write your run-log once, at the end.
