# Knowledge board -- Volitility-Model

Curated project FACTS (curator terminal pass S11, 2026-11-02). Relations that OWNERSHIP/CONTRACT/REVIEW_A already state are pointed at, not restated.

## Governing documents (repo .claude/)
- OWNERSHIP.md: lane map, verifier separation, model plan, corrections log R-1..R-12, user rulings U-A..U-E. Binding over CONTRACT.md.
- CONTRACT.md v1.0 is STALE: never amended, not in commit 1 (U-B). Its 3.4 price-only IV acceptance is SUPERSEDED by R-1/R-2.
- REVIEW_A.md (binding rulings R1-R21; R5 withdrawn), REVIEW_B.md (D1-D13, OX-1..5; section 5 = delta pass), RETRO.md, SPAWN_PROMPTS.md.
- Approved plan = frozen given (path in OWNERSHIP.md header); cite, do not re-derive.

## Environment (not a git repo locally; public remote nygiantsmax-rgb/Volsurface)
- Python 3.13.15 (path in OWNERSHIP.md); numpy 2.5.3, scipy 1.18.1, plotly 7.1.0, pandas 3.0.6 (copy-on-write), yfinance 1.7.0.
- NOT installed: pytest, dash, kaleido. selftest.py/oracle_check.py use plain asserts and exit 1 on failure.

## User rulings (2026-11-02)
- Dashboard = standalone Plotly HTML only (fig.write_html). Synthetic data is the default (no API keys).
- Live team = long-lived spokes relayed by the hub; spokes message only the hub. Flow-lead rules, curator judges.
- Case study (U-D/U-E): THIS PROJECT ONLY; agent-memory craft files ICED; other projects stay isolated both ways.

## Design givens (frozen; do not re-litigate)
- F = S*exp((r-q)T); k = ln(K/F); OTM quotes only. Interpolate total variance w = iv^2*T over (T,k); RBFInterpolator default.
- Fixed-strike term structure uses per-maturity k_i = ln(K/F(T_i)). Arbitrage checks are DIAGNOSTICS, not guarantees.

## Facts established in the build
- IV acceptance (R-1/R-2, bs_pricing.py): Newton accepts only where vega is finite and >= 1e-8 AND |resid|<=tol AND |resid/vega|<=1e-9; else Brent. Price-only tol returned iv=1e-4 for a 3e-10 put. Clean chain: 264 OTM rows, 258 solved, 6 status-2 rows (prices 7.5e-15..1.9e-11 <= 1e-10) are CORRECT per R7/R-2 (R-8), not a defect.
- Spline surface: 56/4680 full-grid butterfly violations sit at extrapolated left-edge nodes (flat clamp + PCHIP in T). In-domain (R9-R11 per-maturity in_domain) it is 0/4348 on the clean chain, reproduced by ORACLE, BUILD-B and QA. K_GRID_MODE stays "union"; do not trim the grid.
- plotly 7: fig.to_dict() base64-encodes arrays; read fig.data[i].z / .customdata. q guard [0, Q_MAX=0.25] in data_io.py; the live ticker q=0.0075 was seen once and its branch not reported (OX-5).

## Harness facts
- Spawn with no model override runs the agent file's model: (sonnet). Actually ran: opus on REVIEW-A, ORACLE, both REVIEW-B; sonnet on builders, QA, HANDOFF, curators, flow-lead, advisor; one haiku probe; CONTRACT lane unverified. Source: RETRO.md (c).
- SendMessage on spokes: MIXED evidence, do not rely on it. A probe spawn and the build lanes lacked it; a later curator spawn held it. Relay stays hub -> spoke, spoke -> hub by final report or file (hub-and-spoke ruling).
- flow-board.py: first call with a backslash path fails; use forward slashes from the repo root (cwd derives the slug). domain-reviewer, memory-curator, handoff-documenter, interface-designer have no Bash: read flow-board.md directly.
- board_read in a run-log is ambiguous (flow board vs this knowledge board); lanes should write both keys. Rollup/duplicate-block mechanics and the 6000-char inject cap: domains\memory-system.md.

## Ship state (S11, 2026-11-02)
- Pushed: commit dcf5428, public repo main; run n and n+1 clean, identical hashes: bs_pricing 12deadc4, synthetic 1414ff07, data_io 589f5c78, surface be111b3e, viz edc7196f, main 900228c8, selftest 34fbf338, oracle_check e44e67b8, requirements 60d0c169, README b0a1b59f. Mutation proof: baseline rc=0, 14 RED, 1 INFO.
- Open at ship (README section 7): D12 (mutation proof attributes RED from failed list, not new_red), D13 (smile mask uses nearest grid row's domain), D7 test half, OX-1/R14 hover, OX-3, OX-4, OX-5. OX-2 closed. R-9 fix round fixed D1, D3-D8, D10, OX-2 (D2/D8 not re-read by the delta pass; D8 confirmed on disk); D9 DEFERRED (R6 enforced by ORACLE comparison); no MAJOR open.
- Judge rate restored to 20 at S10 (verified at S11). The enforcing script is still unbuilt (domains\memory-system.md).
- Next: S12 case-study commit (hub executes CASE_STUDY_PLAN.md).

---
<!-- AUTO-APPENDED LESSONS BELOW (rollup-runlog.ps1) -->

### 2026-11-02 - Volitility-Model / pipeline-builder (consolidated by curator at S11 from all builder rollups)
lesson: ls the repo for the upstream module before writing a guarded-import stub. A narrowed-scope diagnostic needs two anti-vacuity injections (one in-domain node must count, one extrapolated node must not). When a ruling's guard seems met, re-read the loop line by line against each clause (BUILD-A's Newton still divided by vega < 1e-8). A check whose guard is the flag it polices, or whose two sides share one mask, is STRUCTURAL and must be labelled so at the site. A control total that sums the loader's own two outputs cannot fail: anchor it to a raw count or print n/a. A hover/docstring describing a marker style must be re-checked when a NaN gap replaces the marker. Rollup moves an inbox run-log to processed/ soon after writing; rewrite fresh, do not Edit.
friction: first flow-board call used a backslash path in every Bash builder; no SendMessage in builder spokes; several heredoc Python edit scripts and unasserted s.index anchors against the brief; R-2 guard believed met before checked.

### 2026-11-02 - Volitility-Model / flow-lead (consolidated by curator at S11)
lesson: A contract-pass reviewer must stay a hard edge before builders even in live mode: all 11 REVIEW-A CHANGE rulings landed after code existed and forced rework in three lanes; if concurrency is forced the reviewer publishes each ruling to disk as made. A QA gate is not accepted without its mutation table (37/37 included checks that could not fail: D3/D4/D10). At retro, count spawns from meta/transcript records and read the model per lane from the transcript model field; runs.jsonl rows are cumulative snapshots, and a hook fix proven only by replay is a gate never seen red.
friction: one retyped run-log path (pipeline-builder-A vs -BUILD-A); build-lane briefs lacked the attestation line (flow-lead defect); the first retro pass assumed one runs.jsonl row per spawn.
