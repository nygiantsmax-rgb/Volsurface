# RETRO - Volitility-Model (flow-lead, fresh instance, 2026-11-02)

Status: FINAL for this flow. The code is shipped (commit dcf5428); the retro finds process faults, which go to the next flow.
Sources: OWNERSHIP.md corrections log, NEXT_STEPS.md, REVIEW_A.md, REVIEW_B.md (sections 2, 3, 5), SPAWN_PROMPTS.md, the flow board,
the run-logs (inbox/processed), the monitor record runs.jsonl, and the subagent spawn records (agent-*.meta.json plus transcripts).
Paths are written relative or as <HOME>. Role edits below are PROPOSALS; none is applied.

## (a) Timeline by phase (all 2026-11-02, times from the flow board and run records)

| Phase | Time | What happened |
|---|---|---|
| P0 Map | 12:49-12:57 | Plan and givens on the board; flow-lead wrote OWNERSHIP.md (lane map, model plan, verifier separation) and SPAWN_PROMPTS.md; interface-designer wrote CONTRACT v1.0 (12:57). |
| P1 Mode switch and build | 13:00-13:12 | User ruling: batch Workflow stopped after CONTRACT, flow becomes LIVE hub-and-spoke. REVIEW-A re-spawned and ran CONCURRENTLY with BUILD-A/B/C (a deliberate hard-edge loss). BUILD-B landed 13:05, BUILD-A 13:06, ORACLE exit 0 at 13:12. Rulings R-1 (3.4) and R-2..R-5 issued. |
| P1b Machinery | 13:06-13:17 | The score-subagent nudge loop re-nudged the curator on every stop (R-7); hub fixed it (idempotency key) and replayed. Curator stopped, later re-spawned. |
| P2 As-built review | 13:23-13:27 | REVIEW-B (opus) found D1-D11 and OX-1..5; flow-lead issued R-9 (fix round, OX-2 ruling). User pause at 13:27; the TO blocks were saved to PAUSED_R9_TO_BLOCKS.md. |
| P3 Planning pause | 13:28-13:42 | NEXT_STEPS.md and the curator's plan; advisor outside read; user decisions U-A..U-E (U-D then U-E narrowed the case study to this project and iced agent-memory). |
| P4 Resume and fix | 14:03-14:15 | New session; earlier agents unresumable except by id. S0/S1 hub baseline, S2 BUILD-B and BUILD-C fix round, S3 QA fix round with mutation proof. |
| P5 Delta, README | 14:27-14:38 | REVIEW-B delta (fresh instance; D12, D13, D7 test half new, no MAJOR open); HANDOFF README; live ticker smoke run (S5b). |
| P6 Ship | 14:38-14:56 | S7 run n and run n+1 clean with identical hash lists; S8 push dcf5428 verified (ls-remote, fresh clone, remote bytes equal run n+1 hashes). |
| P7 Close | now | S9 retro, S10 judge-rate restore, then S11 curator, then S12 case-study commit (hub executes CASE_STUDY_PLAN.md). |

## (b) Defects, who found them, root cause, reusable rule

| # | Defect | Found by | Root cause | Reusable rule |
|---|---|---|---|---|
| 1 | CONTRACT 3.4 acceptance (price residual <= 1e-8 only) accepts ANY sigma on a ~3e-10 deep-OTM price, so it contradicts CONTRACT 12 (round trip <= 1e-6). Ruled R-1 (Newton also needs abs(resid/vega) <= 1e-9; Brent short-circuits only on exact zero). | BUILD-A (pipeline-builder) while implementing; ORACLE (opus) later judged by observable vol error | The contract stated a tolerance in the wrong quantity (price, not sigma) and nobody tied it to the contract's own end-to-end acceptance section. REVIEW-A's own R5 (relative price rule) was also wrong and was conceded. | Cross-check every tolerance and acceptance rule against the contract's acceptance section in a table of pairs; state tolerances in the quantity being solved for. When a section 12 criterion and a section 3 rule conflict, the acceptance criterion wins and the loser is amended in writing. |
| 2 | R-2 guard (Newton accepts only where vega is finite and >= 1e-8) was believed met but the as-built code divided by vega < 1e-8 and could accept there. | BUILD-A on a second line-by-line pass (own friction line) | Self-model of "done" was recalled, not re-read against each clause of the ruling. | After any ruling edit, re-read the loop against each clause of the ruling and record the line numbers; a claim of done without line numbers is a green marker. |
| 3 | Spline surface: 56/4680 butterfly violations on the clean chain, all at extrapolated left-edge nodes. Ruled R9/R10/R11/R21 (per-maturity in_domain; score only in-domain nodes; K_GRID_MODE stays union). | BUILD-B reported; REVIEW-A ruled; ORACLE reproduced independently (0/4348 in domain) | A domain flag defined against the UNION grid certifies extrapolation as reliable. | Define the domain once per slice and point diagnostics, display and tests at that one definition; add an n_checked floor so narrowing scope cannot yield a 0/0 pass. Do not trim the grid to hide violations. |
| 4 | Score-subagent nudge loop (R-7): the curator was re-nudged about every 30 s (13 repeat-search records, 13:06-13:11). | Flow-lead and hub observation; fixed by hub (main-session) | The nudge had no idempotency key; det_flags were computed over the whole transcript and re-emitted on unchanged evidence. | Any hook that feeds back into the agent it scores needs an idempotency key (agent_id, flag set), proven by a two-stop replay. CAVEAT (evidence below): the fix is proven by replay only; no live repeat-search flag has occurred since, so it has not been seen to fire in anger. |
| D1 | main.py control total was a tautology and the ticker path printed "0 rejected" while fetch drops rows (the one wrong PRINTED number). MINOR. | REVIEW-B | n_read was defined as the sum it then asserted. | Trace both sides of every control total to where each was first counted; if they share an origin it is documentation. Where no independent count exists print n/a. |
| D2 | surface.py CT2 reused the same arrays and was gated by the flag it polices; CT3 an identity. MINOR. | REVIEW-B | "Independent" comment without an independent path. | A comment claiming independence must name the independent path, else label the check STRUCTURAL. |
| D3 | selftest accepted price-only on sub-1e-8 prices (the failure R-1/R-2 forbid). MINOR. | REVIEW-B | Superseded rule kept alive in a test OR clause. | When a rule is superseded, grep tests and docstrings for the old statement. |
| D4 | MAJOR: R13 (a binding CHANGE) had no failing check; the only fixture (clean chain) never triggers the gap, and no mutation touched the viz line. | REVIEW-B | 37/37 green with a check that could not fail. | For every binding ruling demand a fixture where its branch fires, plus a named mutation that turns it red. |
| D5 | viz docstrings and hover text claimed markers that NaN gaps do not render. MINOR. | REVIEW-B | Label stronger than content after a presentation change. | Re-read docs and hover strings when the rendering rule changes. |
| D6 | Stale selftest failure message (k_grid containment vs R10 rule). MINOR. | REVIEW-B | Message not updated with the check. | Messages are part of the check; edit together. |
| D7 | R3 params line not first on csv/ticker paths; no test of ordering. MINOR; code closed, test half still OPEN. | REVIEW-B (delta confirmed test half missing) | Ordering requirement with no assertion. | A "always first" requirement needs a first-line assertion and a mutation that reorders. |
| D8 | Stale data_io docstring contradicted the R2 rule. MINOR. | REVIEW-B | Own stale text left after an edit. | State each relation once; delete the superseded clause. |
| D9 | No test detects a parity put (R6). MINOR, DEFERRED with default in force (enforced by ORACLE direct comparison and reading). | REVIEW-B | Round-trip tolerance cannot see a ~2e-8 IV difference. | Name the failing mutation for each ruling; if none can go red say so in the README. |
| D10 | Mutation `loader_keeps_last_duplicate` reached code no check ran. MINOR. | REVIEW-B | Mutation aimed at the wrong code path. | A mutation must reach the far side of the system: add an anti-vacuity assertion. |
| D11 | Self-test reference ncdf uses a 1-N form at one non-tail point. MINOR, no fix. | REVIEW-B | Not a price path. | None needed. |
| D12 | Mutation-proof attribution took "caught" from the failed list instead of NEW failures and never asserted the baseline green. MINOR, OPEN. | REVIEW-B delta | RED credited without the mutation causing it. | Attribute RED only from new_red and assert baseline rc==0 before trusting any verdict. Mitigation in force: the hub quoted BASELINE rc=0, 14 RED, 1 INFO. |
| D13 | Smile mask uses the nearest grid row's domain, a second definition of the domain; can draw an extrapolated node as data at off-grid T (hand estimate: 0 or 1 node). MINOR, OPEN. | REVIEW-B delta | Second emitter of one value. | One artifact, one emitter: derive from the slice's own quotes. |

Open at ship (README limitations): D12, D13, the D7 test half, OX-1 (R14 hover), OX-3, OX-4, OX-5 (dividend yield unit: observed once, branch not reported). OX-2 is closed.

Also a flow-lead defect (mine): the build-lane SPAWN_PROMPTS blocks lacked an attestation line (BUILD-A, BUILD-C had none), and I retyped one run-log path instead of citing it. Fixed by the standing footer added at the pause; too late for the first spawns.

## (c) Model-plan check (source: agent-*.meta.json plus the model field on transcript messages; runs.jsonl records no model)

| Lane (agent) | Planned | Ran (transcript) |
|---|---|---|
| REVIEW-A (domain-reviewer) | opus | opus (claude-opus-5-5) |
| ORACLE (oracle-verifier) | opus | opus |
| REVIEW-B first pass and REVIEW-B delta (two domain-reviewer instances) | opus | opus, opus |
| BUILD-A, BUILD-B, BUILD-C (pipeline-builder) | sonnet | sonnet each |
| QA (qa-verification-engineer) | sonnet | sonnet |
| HANDOFF (handoff-documenter) | sonnet | sonnet |
| flow-lead live instance, this retro instance, memory-curator x2, advisor | sonnet | sonnet |
| SendMessage probe (a domain-reviewer spawn) | not in plan | HAIKU (2 messages, 0 tools): a downgrade below the sonnet baseline, used for non-domain work, recorded nowhere in the model plan |
| interface-designer (CONTRACT) and the first flow-lead | sonnet | UNVERIFIED: both ran in the Workflow phase and have no subagent transcript on disk; the frontmatter default is sonnet; not inferred |

D-9 (NEXT_STEPS: "builders and QA may have run session opus") is RESOLVED: they ran sonnet. The opus lanes held because the hub passed the model explicitly.

Wrong-number check, stated honestly:
- A sonnet lane DID produce one wrong printed number: BUILD-C's ticker path printed "0 rejected" (D1). It is a printed count, not a computed IV or price. Disposition: fixed in the R-9 round; no escalation of BUILD-C (its other output was independently verified), but recorded here as the escalation trigger the model plan asked for.
- No computed financial number from any sonnet lane was wrong: ORACLE (opus, independent erfc pricer and bisection IV) agreed with the built pricer to 4.3e-14 absolute over 528 clean rows and 5.7e-14 over 7776 points, IV round trip max 9.3e-10 on 258/264 solved rows; REVIEW-B hand-derived the R-1 deep-OTM case.
- The opposite direction also happened: REVIEW-A (opus) printed rounded R16 figures (0.1076, 0.412) that were wrong in the last digit; BUILD-A (sonnet) computed 0.107537 and 0.411 and R-8 corrected them. The tier did not prevent wrong numbers; a read by a different lane caught each one.
- QA (sonnet) shipped checks that could not fail (D3, D4 MAJOR, D10) and, after the fix round, a mutation proof whose attribution could be vacuous (D12). QA is the independent-verification lane and met the escalation criterion; I left it at sonnet in the plan. That was a planning error, evidence D4 and D12. Recommendation for the next flow: pass model: opus for QA whenever it owns the mutation proof, or keep sonnet but require an opus read of the mutation table before the gate counts.

Standing tension (team doctrine: no downgrades; roster baseline sonnet by operator instruction) is unchanged; the plan above is the cheaper baseline plus four explicit opus lanes, and the haiku probe is the only run below baseline.

## (d) Generic-spawn and red-herring check

Generic spawns: NONE. All 15 spawn records on disk name a role (pipeline-builder 3, domain-reviewer 4, memory-curator 2, flow-lead 2 including this one, qa 1, advisor 1, oracle 1, handoff 1); the interface-designer and first flow-lead are named in runs.jsonl and the Workflow phase. The outside read used the advisor role (U-A), not a general-purpose agent. One message to a general-purpose target was attempted by flow-lead and returned "not reachable" (a send, not a spawn).

Red-herring and gate-chase candidates, with evidence:
1. SendMessage probe (haiku spawn plus NEXT_STEPS 5.1 nonce-test plan): outcome-neutral, because one-way relay was the default in force either way; cost one spawn and several paragraphs. Verdict: a gate that did not change the outcome; a cheaper test is reading the spawn's tool list.
2. Case-study scope planning (R-10, R-11, NEXT_STEPS 4a/4b/6b, the curator's NEXT_STEPS_MEMORY section 4): wide scan classes over agent-memory and LESSONS, held first-name file. U-E then ICED agent-memory. Planning that U-E made moot: a red herring in outcome terms, although the scan classes survive for the remaining files.
3. The repeat-search flag on the curator (13 records): the curator did re-Read a file after a Grep (its own friction admits it), but the flag fired every 30 s on unchanged evidence; the real cost was the machinery fix, not the behavior.
4. The 11 on_task=False and 18 pertinent=False judge verdicts (of 154 judged rows) are clustered on long resumed transcripts during the planning pause (flow-lead, curator, advisor rows); treated as judge noise, not chased.
5. D-9 (which model ran): cheap to settle from spawn records once looked at; the delay was not looking.

Not red herrings (changed the outcome): R-1 ratification, the REVIEW-B green-marker hunt (D4 MAJOR), the as-built hash gate at S7.

## (e) Concrete prompt edits (PROPOSALS ONLY; each cited)

SPAWN_PROMPTS.md
- SP-1 Add a first line to every lane block: "Model: <sonnet|opus>; the hub passes model: explicitly and logs it on the board at spawn." Evidence: D-9 stayed unverified until transcripts were read; the opus lanes held only by explicit override (LESSONS spawn-model rule); the haiku probe appears in no plan.
- SP-2 Move the STANDING FOOTER from the end of the file to the head and say it is included in every block by reference. Evidence: BUILD-A and BUILD-C had no attestation (R-8); the footer was written at the pause, after the first spawns.
- SP-3 Footer: add "heredoc_edits: none|<n>" to the attestation lines and repeat "Write/Edit only". Evidence: BUILD-A and QA run-logs report heredoc Python edit scripts against the brief (BUILD-A also used unasserted s.index anchors).
- SP-4 CONTRACT block: add "list every tolerance or acceptance rule in sections 3-9 next to the section 12 criterion it must satisfy, as a pair table." Evidence: defect 1 (3.4 vs 12).
- SP-5 REVIEW-A block: "append each ruling to REVIEW_A.md as it is made; do not publish one FINAL file; re-derive any number you print from source." Evidence: all 11 CHANGE rulings landed after code existed (NEXT_STEPS 5.4); R16 printed figures wrong in the last digit (R-8).
- SP-6 QA block: "for each binding ruling add a fixture where its branch fires and a named mutation; attribute RED from new_red; assert the baseline rc==0 and failed==[] before any verdict." Evidence: D3, D4, D10, D12.
- SP-7 BUILD blocks: "every printed control total takes one side from the producer's own tally or prints n/a; every comment claiming independence names the independent path; after each ruling edit grep your docstrings for the superseded text." Evidence: D1, D2, D8.
- SP-8 HANDOFF and REVIEW-B blocks: add "Read first: CONTRACT sections used, REVIEW_A, the lane's own SPAWN block." Evidence: the HANDOFF run-log (skipped CONTRACT/REVIEW_A until the advisor pointed it out) and the REVIEW-B run-log (had not opened its own block before writing).
- SP-9 Run-log path: cite the path from the block, never retype it (my defect: pipeline-builder-A vs pipeline-builder-BUILD-A).

Role files (~/.claude/agents/*.md), proposals for the owner of those files
- RF-1 All Bash roles: replace the backslash flow-board call with the forward-slash form from the repo root. Evidence: grep of the role files shows the backslash form at the startup block; the BUILD-A, BUILD-B, BUILD-C and QA run-logs report the first call failed.
- RF-2 No-Bash roles (domain-reviewer, handoff-documenter, memory-curator, interface-designer): replace the startup instruction to run flow-board.py with "If you have no Bash, Read the project flow-board.md directly and write board_read: yes|no." Evidence: five run-logs say the board script could not run.
- RF-3 All roles: add "attestation:" and "board_read:" lines to the final-step schema and the write-once rule. Evidence: a grep of the role files found none of these terms; BUILD-A and BUILD-C had no attestation; four roles added board_read ad hoc; run-log versions per lane: BUILD-B 4, BUILD-A 3, BUILD-C 3, ORACLE 3, flow-lead 3, curator mid-flow 3.
- RF-4 Run-log path in every role file reads inbox/<role>.md but OWNERSHIP uses <role>-<LANE>.md; make the block's path authoritative. Evidence: the retyped-path defect.
- RF-5 qa-verification-engineer: add the green-marker rules (named mutation, anti-vacuity assertion, new_red attribution, baseline assert, scratch-copy only with live hash unchanged). Evidence: grep finds none of these terms in the file; D3, D4, D10, D12.
- RF-6 pipeline-builder: add "re-read the loop against each ruling clause and cite line numbers before reporting done" and "ls the repo for the upstream module before writing a stub". Evidence: defect 2; BUILD-B run-log.
- RF-7 domain-reviewer: add "re-derive any number you print from the source, and open the lane block in SPAWN_PROMPTS before writing". Evidence: R16 figures; REVIEW-B friction line.
- RF-8 flow-lead (this file): add to the retro checklist "read the model per lane from the transcripts' message model field and the meta files, never from the frontmatter"; and in startup "confirm cwd is the repo root before flow-board". Evidence: D-9; the slug-from-cwd lesson.
- RF-9 handoff-documenter: add "quote literal print strings, grep the code to confirm; label test-only fixtures". Evidence: HANDOFF lesson.

Machinery (owner: orchestrator or user, not a role file): runs.jsonl lists agent_type "(unknown)" on 100 of 160 rows; 18 of those exactly duplicate the (out_tokens, tool_uses, duration_s) of a typed row, so rows are cumulative SubagentStop snapshots and 117 distinct agent_ids are NOT 117 spawns. The writer should resolve agent_type for every stop and the monitor should key rows by agent.

## (f) Metrics

Counting method: spawns are counted from the meta/transcript records (15 on disk) plus the two Workflow-phase agents seen only in runs.jsonl. runs.jsonl itself (160 rows, 117 agent_ids) is cumulative snapshots and is not a spawn count.
- Agent instances: 17 (REVIEW-A 1, REVIEW-B 2, haiku probe 1, builders 3, QA 1, ORACLE 1, HANDOFF 1, advisor 1, curator 2, flow-lead 3 including the Workflow-phase one and this retro, interface-designer 1). Several were RESUMED for the R-9 round (BUILD-B, BUILD-C, QA) and not re-counted.
- Rulings: lead rulings R-1..R-11 (11); REVIEW_A rulings R1..R21 (21: 9 ACCEPT, 11 CHANGE, 1 SUPERSEDED); user decisions U-A..U-E (5).
- Defects: D1-D13 = 1 MAJOR (D4) and 12 MINOR (D11 no-fix); plus 1 contract-level defect (3.4) resolved by R-1/R-2; plus 5 exceptions OX-1..OX-5 (OX-2 closed, 4 open). Machinery defect: nudge loop (R-7).
- Fix rounds: 1 formal (R-9: BUILD-B D2/D8, BUILD-C D1/D5/D7/OX-2, QA D3/D4/D6/D10) plus the informal in-place rework after REVIEW-A landed late (BUILD-A R-2 guard, BUILD-B R9-R11, BUILD-C R3/R13). No second round was needed.
- Live hub runs documented on the board: pre-pause live run 2, S1 baseline, S5b ticker, S7 run n, S7 run n+1 (S4 is in the plan; not separately evidenced in what I read). S5b: one ETF, exit 0, q 0.0075, in-domain calendar 575/2831 and butterfly 174/2793 (diagnostics, not arbitrage claims).
- S7 gate: PASS. Run n and run n+1 clean, hash lists identical; mutation proof baseline rc=0, 14 RED, 1 INFO. Push dcf5428 verified. Caveat kept visible: D12, D13 and the D7 test half are open MINORs in the shipped commit.
- Monitor facts: 154 of 160 rows LLM-judged (haiku, sample_rate 1 during the flow); 6 rows unjudged. `nudged` first appears at 13:14:44 after the fix and is false on all 68 rows since; the fix has been proven by replay only.
- Effort (final snapshot per typed agent, out_tokens): about 674k output tokens across typed agents; builders 152k, domain-reviewers 112k, HANDOFF 87k, ORACLE 80k, QA 70k, flow-lead 96k, curator 38k, interface-designer 30k, advisor 9k.

## (g) Hand-off list for memory-curator

Routing is allowed for all three classes; agent-memory craft files stay ICED for publication (U-E).

Project facts (knowledge board, above the marker)
- CONTRACT 3.4 price-only acceptance is superseded by R-1/R-2; CONTRACT.md was never amended (U-B, closed and stale; not pushed in commit 1).
- Final shipped state: commit dcf5428 on the public repo main; run n and n+1 hash lists identical (bs 12deadc4, syn 1414ff07, dio 589f5c78, surf be111b3e, viz edc7196f, main 900228c8, self 34fbf338, oracle e44e67b8, req 60d0c169, README b0a1b59f).
- Open at ship: D12, D13, D7 test half, OX-1, OX-3, OX-4, OX-5; R-9 outcome; clean chain 258/264 solved, 6 status-2 rows by R7/R-2.
- Models that actually ran per lane (section c) and D-9 resolved.
- Ticker smoke run observed once; branch for q not reported.

Cross-cutting doctrine (LESSONS head; each already has evidence above)
- Cross-check each contract tolerance against the contract's acceptance section (defect 1).
- A mutation proof must attribute RED from NEW failures and assert the baseline green (D12); a binding ruling needs a fixture where its branch fires (D4).
- A fix to a feedback hook is proven only when the flag has been seen to fire once live; replay alone is a gate never red (nudge loop).
- Count spawns from meta/transcript records, not from monitor snapshot rows; model per lane comes from the transcripts.
- A contract-pass reviewer is a hard edge before builders even in live mode; if concurrency is forced it publishes each ruling to disk as made.
- Judge-rate restore obligations need a start-of-flow check script (already a curator lesson; reinforced by this flow).

Role craft (agent-memory routing only; not published)
- flow-lead: read model-per-lane from transcripts at retro time; put model in each spawn block; QA with a mutation proof meets the opus escalation criterion.
- pipeline-builder: re-read the loop against each ruling clause; no heredoc edits; assert unique anchors.
- qa-verification-engineer: new_red attribution, baseline assert, branch-firing fixtures.
- domain-reviewer: re-derive printed numbers; open your own lane block first.
- handoff-documenter: quote literal strings; label test-only fixtures.

Open items needing the USER are listed in the final report and in CASE_STUDY_PLAN.md section 9.
