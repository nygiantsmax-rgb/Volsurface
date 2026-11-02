# OWNERSHIP - Volitility-Model

STATUS: IN FORCE (first version, 2026-11-02)

Repo root: <REPO> (not a git repo)
Interpreter: <HOME>/AppData/Local/Programs/Python/Python313/python.exe (3.13.15)
Plan (frozen given): <HOME>/.claude/plans/<approved-plan>.md
Board: py <HOME>/.claude/team-memory/bin/flow-board.py --show
Run-logs: <HOME>/.claude/team-memory/projects/Volitility-Model/inbox/<role>-<LANE_ID>.md

## External givens (owned by no lane)
- The approved plan, the flow board givens, user rulings (standalone HTML only, synthetic default).
- Installed libs: numpy 2.5.3, scipy 1.18.1, plotly 7.1.0, pandas 3.0.6 (copy-on-write), yfinance 1.7.0. No pytest, no dash, no kaleido.

## Lane map (acyclic)
Order: CONTRACT -> REVIEW-A -> {BUILD-A, BUILD-B, BUILD-C} -> {QA, ORACLE, REVIEW-B} -> fix round -> HANDOFF -> retro -> memory-curator.
Hard edges: only CONTRACT.md (+ REVIEW_A.md rulings, binding over CONTRACT.md on conflict) and "build done" before verifiers. No cycles: each artifact below has exactly one producer.

| Lane | Role (agent type) | Model | OWNS | CONSUMES | Fallback |
|---|---|---|---|---|---|
| CONTRACT | interface-designer | sonnet | .claude/CONTRACT.md | plan, board | none upstream; plan is the spec |
| REVIEW-A | domain-reviewer | opus | .claude/REVIEW_A.md | CONTRACT.md | rule on plan text if contract thin |
| BUILD-A | pipeline-builder | sonnet | bs_pricing.py, synthetic.py | CONTRACT.md, REVIEW_A.md | none needed (leaf) |
| BUILD-B | pipeline-builder | sonnet | data_io.py, surface.py | CONTRACT.md, REVIEW_A.md; MARKED STUBS of bs_pricing/synthetic functions | stub per contract, swap to real import once A's file exists |
| BUILD-C | pipeline-builder | sonnet | viz.py, main.py, requirements.txt | CONTRACT.md, REVIEW_A.md; MARKED STUBS of Surface/surface.py/synthetic | stub per contract |
| QA | qa-verification-engineer | sonnet | selftest.py | all built code, CONTRACT.md, plan checks 1-8 | selftest checks the contract if a module is missing; report as finding |
| ORACLE | oracle-verifier | opus | oracle_check.py | CONTRACT.md + textbook BS; built code ONLY AFTER oracle written | n/a |
| REVIEW-B | domain-reviewer | opus | .claude/REVIEW_B.md | built code, REVIEW_A.md | hand-derive from source (no Bash granted to this role) |
| FIX | owning BUILD lane(s) | sonnet | the confirmed-finding files of that lane only | QA/ORACLE/REVIEW-B findings | one round max; rest reported |
| HANDOFF | handoff-documenter | sonnet | README.md | final code, CONTRACT.md, REVIEW_B.md | document only what was verified by reading code (no Bash granted) |
| lead | flow-lead | sonnet | .claude/OWNERSHIP.md, .claude/SPAWN_PROMPTS.md | all run-logs | - |
| curator | memory-curator | sonnet | memory stores | flow-lead hand-off | - |

Each source file appears in exactly one OWNS cell. Nobody edits another lane's file; defects go into findings with owner_lane.

## Verifier separation (not tool-enforced; the harness may grant Edit regardless)
- QA, ORACLE, REVIEW-A, REVIEW-B MUST NOT edit bs_pricing.py, synthetic.py, data_io.py, surface.py, viz.py, main.py, requirements.txt. Writes are limited to their own OWNS cell. Run-log MUST attest "did not edit source under test"; a missing attestation is the detector.
- Mutation proof (plan check 8): QA may mutate ONLY a scratch copy under the scratchpad/temp dir, never the live file, and must assert the live file hash is unchanged afterward.
- ORACLE independence: reimplement BS price and IV from CONTRACT.md and the textbook formula; must NOT read bs_pricing.py (or surface.py/synthetic.py internals) before oracle_check.py is written. Run-log states the order of events. Only after that may it import the built module to compare.
- Library modules must not "pass" by import alone; selftest/oracle_check need a real __main__ guard exiting non-zero on failure (LESSONS). Each gate must name its failing mutation (LESSONS green-marker rule).

## Binding rulings
- REVIEW_A.md overrides CONTRACT.md where they conflict. Builders cite the ruling.
- Contract conflicts found by builders: build to the contract with a marked stub, record the assumption in the run-log, do not block.

## Model plan
Default sonnet. ESCALATED to opus by flow-lead: ORACLE (independent verification, financial math), REVIEW-A and REVIEW-B (domain review of financial treatment). Standing tension: team doctrine says no downgrades; roster baseline is sonnet by operator instruction. If any sonnet lane (BUILD-A pricing, QA) produces a wrong number, escalate it in the retro.

## Role-capability notes (agent frontmatter, checked this run)
- domain-reviewer: no Bash. Cannot execute code; REVIEW-B substitutes hand-derivation from source. Not a hole in the map, accounted here.
- handoff-documenter: no Bash. README commands must be copied from main.py argparse/verified run-logs, not executed by it.
- interface-designer: writes no code.
- Shell is PowerShell/Git Bash on Windows: write code with Write/Edit, not heredocs; ASCII-only console output; use PowerShell $LASTEXITCODE for true exit codes.

## Corrections log
- 2026-11-02 MODE SWITCH batch -> LIVE hub-and-spoke (user ruling; board note 13:00). Supersedes the "Order:" line in the lane map where they differ; the OWNS/CONSUMES columns are unchanged.
  - The batch Workflow was stopped after CONTRACT. The main session is the hub and the only spawner; spokes message only the hub; the hub relays to flow-lead for rulings.
  - SEQUENCING CHANGE: REVIEW-A now runs CONCURRENTLY with BUILD-A/B/C instead of before them. Builders receive REVIEW-A CHANGE rulings live, relayed by the hub. RISK: a builder may encode a treatment before the ruling lands, so a ruling can arrive after the code it changes exists. Mitigation: the ruling is binding over CONTRACT.md as before; the hub relays it to the owning BUILD lane with the exact instruction; a builder that already built the other way fixes it in place and notes it in its run-log; REVIEW-B re-checks every ruling against as-built code, so a late ruling cannot slip through unverified.
  - ORACLE and QA start early (writing oracle_check.py from the spec, selftest.py against the contract) while code lands. ORACLE independence rule is unchanged: it may not read built code until oracle_check.py is written.
  - REVIEW-B and HANDOFF still start only after the builds finish.
  - Status line above deliberately NOT re-promoted or edited by this entry.
- 2026-11-02 RULING R-1 (CONTRACT 3.4 implied_vol acceptance; binding over CONTRACT.md 3.4, CONTRACT.md itself stays closed). Defect: 3.4's price-only rule (|price residual| <= 1e-8) is satisfied by ANY sigma on a ~3e-10 deep-OTM price, so it contradicts CONTRACT 12 (clean round-trip <= 1e-6). Ruling: BUILD-A's stricter rule is RATIFIED as the governing behavior: Newton accepts only if |resid| <= tol AND |resid/vega| <= 1e-9; Brent short-circuits only on an exact zero residual. `tol` remains the price-residual tolerance and the signature is unchanged. Section 12 is the acceptance criterion and wins the conflict. Pending: REVIEW-A may refine but not loosen back to price-only. Lanes to re-check: BUILD-A (docstring cites R-1), ORACLE (see below), QA (selftest asserts section 12 round-trip on the clean chain, including the deep-OTM rows), REVIEW-B (as-built check).
  - ORACLE rule: judge by observable behavior, not by acceptance mechanism. For every clean-chain row the oracle's own IV must agree with sigma_true to 1e-6; where its solver and the built one differ, sigma_true is the reference, not the built code. An oracle encoding literal price-only 3.4 is wrong on deep-OTM rows; it must use a vol-space or bracket-width stop.

- 2026-11-02 USER RULING: "team lead and memory curator should be in charge of messaging, decision making, judging and ruling." Effect: (a) flow-lead makes every ruling and writes every lane message; (b) memory-curator judges: checks run-log attestations against disk, judges lanes' memory and board use, posts board broadcasts; (c) the hub is TRANSPORT ONLY: spawns and pastes flow-lead message blocks verbatim (subagents cannot call SendMessage; verified by probe). This SUPERSEDES the earlier "hub may route mechanically by OWNS" standing rule: the hub makes no rulings, including deferrals. Curator's judging role is additive to its terminal memory duty; it owns no source file.
- 2026-11-02 RULINGS R-2..R-5 (flow-lead):
  - R-2 IV acceptance: R-1 governs; REVIEW_A R5 is withdrawn (REVIEW-A conceded) but its guard sentence is binding: Newton accepts only where vega is finite and >= 1e-8; vega < 1e-8 routes to Brent; status 2 = price <= lower_bound + 1e-10 or >= upper_bound - 1e-10; a price in (1e-10, 1e-8] is NOT out_of_bounds. Price-only acceptance forbidden.
  - R-3 R14 (3D hover "extrapolated" tag): DEFERRED by flow-lead (ratifying the outcome, not the hub's authority). Default in force: R13 alone. Open presentation exception: REVIEW-B lists it as open, HANDOFF names it in the README limitations. Reopen only if the fix round has capacity after R3/R13/R9-R11 land and QA's hovertemplate parse can be updated in the same round.
  - R-4 Sequencing: R9-R11 field names (k_lo, k_hi, in_domain, term_structure in_domain) are fixed by REVIEW_A text, so no lane waits. BUILD-C and QA build to those names with marked stubs, then re-run against real Surface when BUILD-B reports done.
  - R-5 REVIEW-B starts only after BUILD-A, BUILD-B, BUILD-C each report all assigned rulings applied (one as-built pass, not two). Spawned on explicit opus.

- 2026-11-02 R-7 MACHINERY DEFECT (outside this map): bin/score-subagent.py re-nudges memory-curator on every SubagentStop because repeat-search is computed over the whole transcript; the loop does not converge. Owner of the fix: orchestrator/user (team-memory machinery), not any lane. Curator STOPPED until fixed; its judging pass (attestations, board/memory use) resumes as a fresh spawn after the fix. Recommended fix (a): nudge once per (agent_id, flag set).

- 2026-11-02 R-8 (flow-lead, after curator judging + ORACLE/BUILD reports):
  - Corrections-log rulings R-1..R-8 BIND over CONTRACT.md exactly as REVIEW_A.md does; CONTRACT.md stays closed (no edit, no version bump). The written amendment of 3.4 is R-1+R-2 here; the README (HANDOFF) states the governing rule and says CONTRACT 3.4's price-only text is superseded.
  - EVERY lane (build, FIX round, QA, ORACLE, REVIEW-B, HANDOFF) must put one line in its run-log: "attestation: edited only <its OWNS files>". Gap: the build-lane SPAWN_PROMPTS blocks lacked it (flow-lead defect); BUILD-A and BUILD-C attested in their final reports. 
  - Each run-log is written ONCE, at the end (rollup duplicates board blocks per version; curator merged five copies).
  - Clean-chain 6 status-2 rows (prices 7.5e-15..1.9e-11 < BOUND_EPS) are correct by R7/R-2, not a spec defect; 258/264 solved, above the 90% bar.
  - R16 printed numbers must be the computed ones (theta(2)=0.107537, 0.411), not the rounded text in REVIEW_A: a docstring number must trace to a computation. Conditions (<4) unchanged.
  - Oracle looser than built on low-vega rows (1.17e-7 vs 6.2e-10) but inside the 1e-6 bar: no action.

- 2026-11-02 R-9 FIX ROUND (flow-lead, from REVIEW_B.md; one round, owners fix own files only):
  - FIX: D4 (MAJOR, QA: R13 check must be able to fail), D3, D6, D10 (QA); D1, D5, D7 (BUILD-C); D2 comment-only, D8 (BUILD-B). D11 none.
  - OX-2 RULED: apply the R13 principle to the smile panel (out-of-domain points y=NaN, trace names unchanged), owner BUILD-C; QA asserts it. If BUILD-C cannot land it this round it becomes a named README open exception.
  - DEFERRED with default in force: D9 (no test detects a parity put; R6 is enforced by ORACLE direct-formula comparison plus REVIEW-B reading; REVIEW-B concedes its R6 rationale overstated the IV impact, about 2e-8 on its hand row). OX-1 (R14), OX-3, OX-4, OX-5 stay README open exceptions.
  - REVIEW-B's agent-memory self-edit is NOT a separation violation (own craft store, not source under test).
  - After the round: hub runs live and reports hashes; REVIEW-B does a delta read of viz.py (D5, OX-2, R13) and the selftest R13 mutation only. HANDOFF after that.

- 2026-11-02 USER DECISIONS (via hub), recorded by flow-lead:
  - U-A Outside read of the board/defects: the ADVISOR role (no stake in the outcome), read-only; not general-purpose (doctrine: no generic spawns).
  - U-B CONTRACT.md is NOT pushed (stale against R-1..R-9; local path on line 4).
  - U-C Repo github.com/nygiantsmax-rgb/Volsurface is empty; public is acceptable. PUSH SET: bs_pricing.py, synthetic.py, data_io.py, surface.py, viz.py, main.py, requirements.txt, README.md, selftest.py, oracle_check.py, .gitignore. Gate before push: grep the staged tree for local paths (<HOME>...) and secrets. Nothing under .claude/ and no vol_surface.html.
  - Transport fact: agents cannot address each other (SendMessage "not reachable"); only the hub spawns or resumes. Hub-and-spoke stands.

- 2026-11-02 USER RULING U-D (ONE-TIME, this push only, NOT a standing setting; supersedes U-B for this push): publish a CASE STUDY under case-study/ in the public Volsurface repo, separate from the code, with all four scopes: (1) .claude/ flow artifacts incl. CONTRACT.md, REVIEW_A/B, NEXT_STEPS(+_MEMORY), PAUSED_R9_TO_BLOCKS, RETRO when written; (2) team-memory/projects/Volitility-Model/ (flow board, knowledge board, inbox and processed run-logs, runs.jsonl); (3) ~/.claude/agents/*.md plus the agent-memory craft files; (4) team-memory/bin/ and config/. Redaction by the user: <HOME> -> <HOME>, drop session IDs, content otherwise unchanged. This is a one-time override of the doctrine "machinery stays out of public git"; the doctrine is unchanged for future flows.
  - flow-lead rulings on execution (R-10): (a) redact a STAGING COPY only; sources are never edited, asserted by hash before/after. (b) Redaction must cover all path forms (<HOME>, <HOME>, escaped <HOME>, URL-encoded), the email address, and UUID-shaped session IDs. (c) The scan is run by a DIFFERENT tool than the redactor (plain grep over the staging tree), so it is not a self-check. (d) The scan is WIDENED beyond the hub's proposal: secrets/tokens (ghp_, sk-, AKIA, bearer, api_key, password), email addresses, personal names/handles other than the intended repo owner, dollar amounts, tickers, account/broker/cost-basis/employer/GL/workbook terms, other-project names. (e) Any hit in the financial/employer/personal categories HOLDS the push for the user; the hub lists file:line. Default for a held file: EXCLUDED and named in a manifest, never silently dropped and never silently included. (f) agent-memory and LESSONS carry other projects' material (<other-project>, <other-project>): included only after its scan is clean or the user clears each hit. (g) Two commits: code first (gated by run n+1, unchanged), case-study second AFTER the curator terminal pass (S11) so it contains the retro and final board. (h) case-study/INDEX.md (flow-lead) explains scope, redaction method, that files are unedited apart from redaction, and that paths inside them do not exist in the repo.

- 2026-11-02 R-11 (flow-lead, after curator Q4 and advisor Q5; refines R-10, same one-time scope):
  - runs.jsonl is NOT published raw. Publish a DERIVED table by field allowlist (agent_type, lane, tool counts, flags, judge booleans); drop session_id, transcript_path, task and judge.rationale. This narrows the user's scope-2 choice for one file, so it is listed in MANIFEST and put to the user (default: derived).
  - agent-memory (scope 3) defaults to EXCLUDED until each file is READ and classified clear / generalize / hold by memory-curator (patterns cannot catch semantic leaks); the user approves the classified list, not each file. dependency-doctor/onedrive-synced-project-tree.md and its index line are held (user's first name).
  - Out of scope, excluded: LESSONS*.md, RESUME.md, HANDOFF.md, state/, *.log, all *.bak* (including score-subagent.py.bak-20261102-nudgeloop and the monitor-config backup), and other projects' directories.
  - Extra scan terms: ~/.claude-less paths, $env:USERPROFILE, expanduser, machine name, the user's first name and university identity (<user>, <university>), and a digit-run grep (4+ digits) over agent-memory. Secret regex bounded: \bsk-[A-Za-z0-9]{20,}; allow-list only nygiantsmax-rgb. The term list lives in a scratch script, not in the repo.
  - INDEX wording: NOT "unedited". State what was changed: home path, session IDs and transcript paths removed; held files excluded; runs table derived.
  - .gitignore anchored: /.claude/, /vol_surface.html, __pycache__/, *.pyc (an unanchored .claude/ would drop case-study/.claude). Gate: git ls-files case-study == the staging manifest.
  - Code push gate: files byte-identical to the run n+1 hashes; README/docstrings/comments grep-clean of <home-dir>, <user>, <user>, OneDrive, scratchpad (read-only grep at planning time: code files and requirements.txt are CLEAN today); requirements pins present; no .pyc; no vol_surface.html; README must say a case-study/ folder exists.
  - SPAWN_PROMPTS.md now ends with a STANDING FOOTER (run-log once, attestation + board_read lines, forward-slash flow-board call, no cross-agent messaging, no local paths in code).

- 2026-11-02 USER DIRECTION U-E (answers NEXT_STEPS 6b; refines U-D/R-10/R-11; status line untouched): "the goal is to include the routing, agent decisions, scoring, and metrics, leaving out unnecessary data not pertinent to this project; first focus on how to finish the project and getting ready for push; external thought files are a topic we can ice for now."
  - PRIORITY ORDER: (1) finish the project, (2) code push, (3) case study.
  - Case-study scope is THIS PROJECT ONLY: routing (OWNERSHIP, SPAWN_PROMPTS), decisions/rulings (corrections log, REVIEW_A/B, RETRO, NEXT_STEPS), scoring and metrics (the DERIVED runs table), the flow board, the knowledge board, this project's run-logs (inbox + processed). Nothing from other projects.
  - ICED (deferred, not in this push, not in S11): all agent-memory craft files; hence the first-name file is moot. Raw runs.jsonl stays out. LESSONS*, RESUME, HANDOFF, state/, logs, *.bak* stay out.
  - Not named by the user, flow-lead default: agent role definitions (agents/*.md) are routing, so INCLUDED after the independent scan; bin/ and config/ (hook machinery) EXCLUDED for now, except that the derived runs table states how the scores were produced. Reversible on request.
  - --ticker smoke run: yes. U-1..U-5 keep defaults. Push: normal git push.
  - No R-9 TO block changes; PAUSED_R9_TO_BLOCKS.md is pasted verbatim at S2.

- 2026-11-02 R-12 (flow-lead, retro pass; status line untouched): RETRO.md and CASE_STUDY_PLAN.md written (both published in commit 2). Model plan check from spawn transcripts: opus ran on REVIEW-A, ORACLE and both REVIEW-B instances; builders, QA, HANDOFF, curators, advisor and flow-lead ran sonnet; one haiku probe (a domain-reviewer spawn) ran below baseline; interface-designer and the first flow-lead are unverified (no transcript). D-9 resolved. Escalation finding: QA owns the mutation proof and met the opus criterion; D4 (MAJOR) and D12 show it should have been escalated or opus-read. Role-file and SPAWN_PROMPTS edits are PROPOSED in RETRO.md section (e), not applied.

- 2026-11-02 USER DECISIONS U-F (answers CASE_STUDY_PLAN section 9 and the RETRO edits; status line untouched):
  1. Four role files that never ran (accuracy-first-scripter, big-picture-strategist, dependency-doctor, env-doctor): EXCLUDE.
  2. oracle-verifier.md, domain-reviewer.md, memory-curator.md: GENERALIZE in the staging copy only (other-project details to <other-project>, routing text kept readable); live files unchanged.
  3. CONTRACT.md with a "superseded in part" header: ACCEPT.
  4. Other-project names in boards and logs redacted to <other-project>: ACCEPT.
  5. Pseudonymous agent_ordinal column in the derived runs table: ACCEPT.
  6. SP-1..SP-9 and RF-1..RF-9: NOT NOW; remain proposals in RETRO.md, published in the case study, not applied.

## Terminal obligations
- flow-lead retro, then restore judge rate: copy team-memory/config/monitor-config.json.bak-sr20 over monitor-config.json and assert sample_rate == 20, as the last act before memory-curator.
