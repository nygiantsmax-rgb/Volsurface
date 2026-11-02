# NEXT_STEPS - Volitility-Model (flow-lead, planning only, 2026-11-02)

Status of this document: PLAN, nothing here is executed. Authority: OWNERSHIP.md corrections log R-1..R-9 binds
over CONTRACT.md. The memory/knowledge-board side is memory-curator's section, merged below when the hub forwards it
(NOT written here).

State at pause (facts, from the flow board 13:27/13:28 and disk):
- Last green live run: bs 12deadc4, syn 1414ff07, dio 3f0a1939, surf af6a5f38, viz b352af85, main ac2ab824,
  selftest efd3db20 (main exit 0 rbf and spline/strike, 5 module self-checks exit 0, oracle 108/108, selftest 37/37).
- selftest.py on disk (mtime 13:26) is NOT efd3db20-trusted: QA was stopped mid-edit. No backup of efd3db20 exists
  (not a git repo). Treat the current selftest.py as UNTRUSTED until step 3 gates.
- R-9 fix-round TO blocks are saved undelivered in .claude/PAUSED_R9_TO_BLOCKS.md. REVIEW_B.md lists D1-D11, OX-1..5.
- monitor-config sample_rate is 1 (restore owed). 

## 1. Resume sequence (lane / trigger / gate = evidence that ENDS the step)

S0 HUB (transport). Trigger: user says resume.
  Do: record sha256 of every file in repo root; copy selftest.py to the scratchpad as selftest.paused-copy.py (the only
  rollback available); confirm no lane is still running.
  Gate: hash list written to the flow board via --note.

S1 HUB baseline. Trigger: S0.
  Do: run the 5 module self-checks, oracle_check.py, selftest.py, main.py (rbf; spline/strike), each with PowerShell
  $LASTEXITCODE (not a bash pipe tail). Report exit codes and hashes.
  Gate: a table of exit codes. Expected: modules/oracle/main 0 on the green hashes. selftest.py may fail or be
  syntactically broken; that outcome is data, not a defect of any lane.

S2 BUILD-B and BUILD-C in PARALLEL (sonnet). Trigger: S1 done. Blocks: PAUSED_R9_TO_BLOCKS.md, pasted verbatim.
  BUILD-B: D2 (comment only), D8 (docstring only). BUILD-C: D1, D5, D7, OX-2 (smile panel NaN gaps, R13 principle).
  Gate per lane: final report with PowerShell exit codes, new hashes, attestation "edited only <OWNS files>", run-log
  written ONCE; BUILD-C shows smile NaN indices == in_domain False indices on the default noisy chain at T=1/12 (or
  states plainly it did not land; then OX-2 becomes a named README exception per R-9).

S3 QA resume (sonnet). Trigger: S2 done and BUILD-C's done notice pasted (QA's OX-2/D4 assertions depend on viz.py).
  Handling the half-edited selftest.py: QA owns the file and completes FORWARD. Its interrupted list (round-trip
  deep-OTM, in_domain independent, R10 false case, main disclaimer, notes printing) plus D3, D4, D6, D10 from the R-9
  QA block. First action: py_compile the file; fix syntax if broken; then re-run. Do not revert (no good copy).
  Gate (all required): selftest exit 0 (PowerShell); D4 mutation table: each named mutation run on a SCRATCH copy goes
  RED, with an anti-vacuity assertion that the mutation reached the far side; live-file hashes of every source under
  test unchanged before/after; D3 price-only clause gone; run-log once with attestation "edited only selftest.py".
  Risk accepted: QA is the lane that shipped 37/37 with a check that could not fail (D4). Mitigation is S5.

S4 HUB live run on the new bytes. Trigger: S3 done.
  Do: repeat S1. Gate: exit-code table + new hashes for every changed file.

S5 REVIEW-B delta pass (domain-reviewer, explicit opus, no Bash). Trigger: S4 green. Block: the delta block in
  PAUSED_R9_TO_BLOCKS.md. Gate: dated delta section appended to REVIEW_B.md; D3, D4, D5, D1, D7, OX-2 each marked
  closed with file:line, or open with owner_lane; "edited only .claude/REVIEW_B.md" attested. A MAJOR still open gets
  one micro-round (that owner only, then S4 again); MINORs go to the README as open.

S6 HANDOFF (handoff-documenter, sonnet, no Bash). Trigger: S5 gate. Block: my HANDOFF block (earlier message).
  Gate: README.md exists; every command traces to main.py argparse or a run-log; states R-1/R-2 governing rule and
  that CONTRACT 3.4 price-only text is superseded; lists OX-1..OX-5, D9, the 56 extrapolated spline nodes, noisy-chain
  counts (tick rounding as untested hypothesis unless QA's tick=0 measurement says otherwise); no PASS counts cited
  as assurance; attestation "edited only README.md".

S7 HUB ship loop (user's ship rule). Trigger: S6.
  Do: run live and UNSANDBOXED from the repo root: main.py default synthetic, both --method rbf and spline/strike,
  all module self-checks, oracle, selftest. Failure => hub sends the exact failure text to flow-lead; I rule owner_lane
  and write the TO block; the hub spawns that owner; hash and re-run. Loop until a run is clean (run n). Then ONE
  more run n+1 on byte-identical files (hash list equal to run n).
  Gate: run n+1 clean AND hashes(n+1) == hashes(n) == hashes of the tree to be pushed. Any file change resets the count.
  Also (non-gating, see D-3): one live --ticker smoke run; a failure there is a README note, not a push block.

S8 HUB push. Trigger: S7 gate. Do: per section 4 and D-4. Gate: pushed tree hash list equals S7 list; remote file list
  equals the proposed set; repo visibility confirmed per D-1/D-4.

S9 FLOW-LEAD retro (sonnet). Trigger: S8 (the push cannot change; retro finds process faults, which go to the next flow).
  Reads every run-log; outputs concrete agent-prompt edits (section 5), generic-spawn and red-herring-chase check
  with evidence, model-plan check (which lanes actually ran opus vs sonnet; see D-9). Gate: retro written to
  run-log + a hand-off list for the curator.

S10 JUDGE-RATE RESTORE (flow-lead, last act before the curator). Trigger: S9. Do: copy
  team-memory/config/monitor-config.json.bak-sr20 over monitor-config.json; assert sample_rate == 20.
  Gate: the assert output. (Do not run earlier: the ship loop may spawn fix lanes that should be judged at rate 1.)

S11 MEMORY-CURATOR terminal pass (fresh spawn, sonnet; judge role per the user ruling). Trigger: S10. Input: my
  retro hand-off + curator's own plan section. Gate: curator's report; lessons routed (cross-cutting to LESSONS head,
  role craft to agent-memory, project facts to the knowledge board).

## 2. Open decisions and the default in force

D-1 USER. Is CONTRACT.md pushed? Default: NO (differs from your proposal). Reason: CONTRACT.md is closed and stale in
    several places that REVIEW_A/R-1..R-9 changed (3.4 acceptance, 6.1 Surface fields, 6.4 disclaimer, 6.6). The rulings
    live in the excluded OWNERSHIP.md, so a pushed CONTRACT.md would contradict the code. The README carries the
    design and governing rules instead. If you want it anyway: push it with a one-line header "superseded in part by
    README 'Governing rules'". That is a lead/hub edit (not a lane), costs one step, and creates a second statement
    of each relation, which I advise against.
D-2 Push selftest.py and oracle_check.py? Default: YES. They are the verification evidence a reader needs. 
    (They are "code"; excluded set stays the .claude/ flow artifacts and vol_surface.html.)
D-3 USER. Live --ticker smoke run (network, yfinance)? Default: one run, non-gating, result stated in README. It is
    also the only thing that can settle OX-5 (the Yahoo dividendYield unit): print both q fields once and record them.
D-4 USER. Remote state of github.com/nygiantsmax-rgb/Volsurface: visibility, existing content, auth. Default: if
    non-empty or public-and-unexpected, STOP and ask; never force-push; git init with a .gitignore (vol_surface.html,
    __pycache__/, *.pyc, .claude/). Standing doctrine says machinery repos stay private; this is a project repo, so
    visibility is your call.
D-5 R14 (3D "extrapolated" hover tag): stays DEFERRED (OX-1). Reopen only on user request; cost: BUILD-C + QA hover
    parse + REVIEW-B delta, one more S4/S5 cycle.
D-6 OX-3 noisy in-domain butterflies, OX-4 vertical-spread bound unchecked: README open exceptions, no fix.
D-7 Second fix round: only for a MAJOR in the S5 delta; one micro-round.
D-8 Does a changed hash after S4 force an ORACLE re-attest? Default NO when the change is docstring/comment-only
    (hub re-run on the changed tree is the evidence, ruled earlier); YES (hub re-run, nothing more) for any code edit.
D-9 Model plan vs what ran: unverified for BUILD-A/B/C and QA (frontmatter says sonnet; hub says possibly session
    opus). Default: no restart; the retro records the real spawn model per lane. For S5 REVIEW-B and any ORACLE work,
    explicit opus override is mandatory.
D-10 Ruling authority: flow-lead rules and writes every message, curator judges, hub is transport only (user ruling).
    Default holds for the ship loop: the hub does not decide owner_lane or fixes, it forwards the failure text to me.

## 3. Remaining terminal obligations
- Retro (S9). Judge-rate restore (S10): sample_rate currently 1; restore from monitor-config.json.bak-sr20 and assert 20.
- Curator terminal pass (S11), fresh spawn.
- Ship rule (S7): live, unsandboxed, run/debug/run until clean, then run n+1, then push (S8). n+1 must be on the exact
  bytes that are pushed.

## 4. What to push (ruling)
PUSH: bs_pricing.py, synthetic.py, data_io.py, surface.py, viz.py, main.py, requirements.txt, README.md,
      selftest.py, oracle_check.py, .gitignore (new, ignore list above).
DO NOT PUSH: .claude/ (OWNERSHIP, SPAWN_PROMPTS, REVIEW_A/B, NEXT_STEPS, PAUSED_*), vol_surface.html (generated
      artifact, reproducible from main.py), CONTRACT.md (see D-1 default).
Before push: grep the staged tree for secrets/keys (none expected; synthetic default, no API keys) and for local
absolute paths (<HOME>...). README must not contain local paths; that is a HANDOFF gate item.
Disclosure/IP: REVIEW_A recorded none (synthetic data, no employer identifiers).

## 5. Process changes for the rest of this flow (cause -> rule -> where it lands)
1. SendMessage on spokes: EVIDENCE IS MIXED. A domain-reviewer probe (haiku, after the tools-line edit) reported it
   unavailable and also showed Edit/advisor not on its line; memory-curator's spawn reported SendMessage present with a
   toolset matching its line exactly. Neither is proven end to end. My own SendMessage to the curator and to general-purpose
   just now returned "not reachable" (they are not live), which proves nothing about delivery. Proof test: after a
   session reload, one spoke sends NONCE-<n> to main and the hub confirms. Until then: treat all spokes as one-way.
   Rule: treat all spokes as one-way. Every spawn block ends with "Report cross-lane findings in your FINAL response as
   findings with owner_lane and file:line; do not wait for replies; you cannot message anyone." Do not rely on the tools
   edit; re-probe once after a session reload and record the result on the board. A reply to a spoke is a resume.
2. Nudge loop (score-subagent): fixed with prior_flags() union (backup .bak-20261102-nudgeloop). Rule: verify by replay
   at the next flow start; any monitor nudge needs an idempotency key per (agent_id, flag set).
3. Run-log rewrites duplicate board blocks (rollup appends per VERSION). Rule: write the run-log ONCE, at the end;
   progress goes in the final response. Add this line to every SPAWN_PROMPTS block before the next spawn (lead edit).
4. REVIEW-A landing after the builders (cause: batch stopped, live mode ran REVIEW-A concurrently). Measured cost: 11
   CHANGE rulings (R2,R3,R6,R9,R10,R11,R12,R13,R14,R16,R21) all landed after code existed; real rework: BUILD-A R-2 guard
   (bs_pricing.py 223-228), BUILD-B R9-R11 plus Surface fields, BUILD-C R3/R13. Rule for future flows: a contract-pass
   reviewer is a HARD EDGE before builders even in live mode; if concurrency is forced, the reviewer publishes each ruling
   to disk as it is made, not one FINAL file. The corrections log already says builders may encode a treatment first.
5. Attestation gaps (BUILD-A, BUILD-C lacked "did not edit other lanes' files": my SPAWN_PROMPTS defect). Rule: one
   attestation line in EVERY lane's brief, "attestation: edited only <OWNS files>", missing line = detector. Already in
   the R-9 blocks; add to SPAWN_PROMPTS for any future spawn.
6. Single source for paths: I mis-typed a run-log path (pipeline-builder-A vs -BUILD-A). Rule: never retype a path; cite
   the SPAWN_PROMPTS line. Hub pastes my blocks verbatim; a paraphrase is a defect.
7. Green markers: QA's 37/37 contained checks that could not fail (D4, D3, D10); REVIEW-B caught them. Rule for this
   flow: no QA gate is accepted without its mutation table, each mutation shown RED (LESSONS green-marker rule);
   S5 re-checks D4 by an independent read.
8. Machinery boundaries: hooks/scripts under team-memory are outside OWNERSHIP; defects go to the orchestrator/user.

## 4a. ONE-TIME CASE-STUDY PUSH (user ruling U-D, supersedes the CONTRACT.md exclusion for this push only)
New step S12 (after S11, flow-lead plans, hub executes): second commit adding case-study/ with four subfolders:
  case-study/flow-artifacts/ (.claude/*.md incl. CONTRACT.md, RETRO), case-study/team-memory/ (project board, run-logs
  inbox+processed, runs.jsonl), case-study/agents/ (agents/*.md + agent-memory craft files), case-study/machinery/
  (team-memory/bin, config), plus case-study/INDEX.md.
  Steps: (1) hub copies sources to a staging dir outside the repo, hashes sources; (2) redact the COPY: <HOME>,
  <HOME>, <HOME> and URL-encoded forms -> <HOME>; UUID session IDs dropped; email redacted;
  (3) re-hash sources: must be unchanged; (4) INDEPENDENT scan (grep, not the redactor) over staging for: <HOME>
  in any form, email, UUIDs, secret patterns, other personal names/handles, dollar amounts, tickers, account/broker/
  cost-basis/employer/GL/workbook terms, other-project names; (5) any hit in financial/employer/personal classes HOLDS
  for the user (hub lists file:line); held files default EXCLUDED with a manifest; (6) commit/push case-study only.
  Gate: zero hits in the hard classes (paths, email, UUIDs, secrets); every soft-class hit cleared by the user or its
  file excluded and listed in case-study/MANIFEST.md.
  Risk accepted by the user: public machinery, hooks and role prompts. Highest risk files: agent-memory (other
  projects), LESSONS-derived text, runs.jsonl (may embed prompts/paths), hooks/config.
  The code push (S8) is unchanged: code files only, own path/secret grep.

## 4b. R-11 refinements to 4a and the main sequence (curator Q4 + advisor Q5 + advisor read, adopted)
Changes to the sequence in section 1:
- S3 gate adds: the hub runs QA's named mutation scratch copies ITSELF and pastes the RED output plus the unchanged
  live-file hashes. REVIEW-B (no Bash, S5) cannot see red, so S5 reads and the hub proves. selftest.py carries no
  absolute local paths (footer rule).
- D-3 ticker smoke run moves BEFORE S6 (call it S5b): the README states OX-5, so its observation is needed first.
- S6 HANDOFF block gains: README has a short "Case study" section pointing to case-study/INDEX.md and must not claim
  nothing from .claude/ is published.
- S1/S8 and section 4: the code push is code + README + requirements.txt + selftest.py + oracle_check.py + .gitignore
  (anchored). Pre-push gate in OWNERSHIP R-11 (byte-identical to run n+1, grep-clean, pins, no .pyc/html).
Changes to S12 (case study), all in OWNERSHIP R-11:
- Publish a derived runs table, not runs.jsonl. Exclude LESSONS*, RESUME, HANDOFF, state/, *.log, *.bak*, other projects.
- Agent-memory is EXCLUDED by default; memory-curator reads and classifies every file (clear / generalize / hold) in
  case-study planning inside its S11 pass; the user approves the classified list. Held: dependency-doctor
  onedrive-synced-project-tree.md + its index line.
- Not yet scanned by anyone: .claude/*.md flow artifacts, agents/*.md, bin/, config/. The hub runs the independent scan
  on those too (S12 step 4); the curator did not cover them.
- S12 also runs: grep of agent-memory for 4+ digit runs; machine name; first name; university identity.
- INDEX.md says what was changed (see R-11), not "unedited".
Section 5 trim (advisor): item 1 stays short; items 6 and 8 are dropped from the in-flow list (they are retro material);
items 2 and 4 move to the retro (S9). Board hygiene: flow-lead posted a RULINGS INDEX note on the board (supersedes lines 5,
the 'ONLY main' rule, and step (7)); the curator curates the facts above the marker (R-2, 3.4 superseded, status-2 rows
per R-8, REVIEW_B pointer, 0/4348, R-9 outcome and final hashes after HANDOFF; drop nothing; no OX list).
Curator/advisor routing adopted: SPAWN_PROMPTS footer (done), rollup dedup guard (user decision U-4), LESSONS head: extend the
hub-and-spoke bullet and promote the nudge-idempotency lesson (curator, S11).

## 6a. ANSWERED by the user (2026-11-02, recorded in OWNERSHIP.md corrections log)
- Outside read: ADVISOR role, read-only. D-1: CONTRACT.md NOT pushed. D-4: repo empty, public acceptable.
- Push set is final: the 8 code/doc files + selftest.py + oracle_check.py + .gitignore (section 4 minus CONTRACT.md,
  which is out). Pre-push gate: staged-tree grep for local paths and secrets; push auth still unverified (hub reports).
- STILL OPEN for the user: D-3 (ticker smoke, default YES) and U-1..U-5 below (defaults hold).

## 6c. USER DIRECTION U-E applied (OWNERSHIP corrections log; supersedes 6b items 1-6 where they differ)
- Priority: finish the project (S0-S7), push the code (S8), case study last (S12).
- Case study is this project only: routing, rulings, derived runs table (scoring/metrics), flow + knowledge board, run-logs.
- Agent-memory ICED (also removes it from the S11 curator work); raw runs.jsonl out; bin/ and config/ out by default;
  agents/*.md in by default. All other 4a/4b gates (staging copy, independent scan, manifest, anchored .gitignore) stand.
- Resume now at S0. No change to the R-9 TO blocks.

## 6b. FINAL user-decision list (supersedes the open items in section 6; defaults hold)
1. Derived runs table instead of raw runs.jsonl (narrows your scope-2 choice for one file). Default: derived.
2. Agent-memory: published only after the curator's file-by-file clear/generalize/hold list is approved by you.
   Default: excluded. Also name your choice for <other-project> / <other-project> / <other-project> names in the board, run-logs
   and agent-memory: keep the project names, or generalize. Default: held until you choose.
3. First name in dependency-doctor onedrive-synced-project-tree.md and its index line: exclude (default) or edit the
   staging copy.
4. D-3 live --ticker smoke run (before S6). Default: yes.
5. U-1 SendMessage edit (keep with guard and nonce test, default; or revert), U-2 flow-start config check, U-3 judge
   re-run keyed on transcript hash, U-4 rollup dedup guard, U-5 keep MAX_CHARS 6000. Defaults: yes to all five.
6. Push auth for the public repo is unverified (gh not installed): the hub tries a normal push and reports.

## 6. Needs the USER's decision (merged: flow-lead D-x and curator U-x; defaults hold until you answer)
(D-1 and D-4 below are now answered in 6a; kept for the record.)
Flow-lead items:
- D-1 Push CONTRACT.md? Default NO (stale vs R-1..R-9, and line 4 holds a local path; repo is public).
- D-3 Live --ticker smoke run (non-gating; only way to settle the Yahoo dividendYield unit, OX-5)? Default YES.
- D-4 Repo: github.com/nygiantsmax-rgb/Volsurface is EMPTY (git ls-remote, no refs, exit 0, no auth prompt). UNVERIFIED:
  public/private (gh not installed) and push auth. You said public. Default: hub tries a normal push after S7; if auth
  fails it stops and reports, never works around it. Public means: no local paths/secrets in the staged tree (gate in S8).
Curator items (recommendations in NEXT_STEPS_MEMORY.md section 4; my view added):
- U-1 Keep the SendMessage tools edit? Curator: keep, guarded (briefs say "to: main only", score-subagent flags any
  other target, nonce test after reload). My view: agree to the guard and test, but the edit conflicts with the hub-and-spoke
  ruling and the evidence is mixed, so the flow keeps running ONE-WAY until the nonce test passes; revert from
  ~/.claude/agents-backup-20261102-sendmessage/ if the guard is not wanted.
- U-2 Flow-start check script that diffs monitor-config.json against .bak-sr20 and fails loudly (check, not silent
  auto-restore). Curator and I agree: YES.
- U-3 Key the LLM-judge re-run on (agent_id, transcript hash). Curator: YES, narrowly. I agree (cost, not correctness).
- U-4 Dedup guard in rollup-runlog.ps1 (skip a block whose lesson text already exists). Curator: YES, back up and prove
  with a two-append replay. I agree; it fixes the root cause of the repeated board blocks and the LESSONS cap.
- U-5 Keep MAX_CHARS=6000, curate the board head under about 5000 chars, no cap change. Both agree: YES.
- Plus: spawn general-purpose or the advisor role for an outside read? Default: advisor (no generic spawns).
Everything else runs on the defaults in section 2.

## 7. Memory-curator's section
Authored by memory-curator, NOT restated here: .claude/NEXT_STEPS_MEMORY.md (judging plan section 1, routing plan 2,
board hygiene 3, user decisions 4, terminal-pass order 5). Its order matches S9-S11 above: my retro, then my
judge-rate restore, then its terminal pass, which Greps sample_rate == 20 first. It has no Bash, so every hash it
compares is hub-reported; the hub supplies the final hash list at S11. Merge notes only:
- Curator wants QA, HANDOFF and the BUILD-B/BUILD-C R-9 logs on disk before it judges them (they owe run-logs); S11
  must not start until S2, S3 and S6 logs exist. BUILD-C has no attestation in any processed/ copy: its R-9 log must carry one.
- Seven lanes have duplicate run-logs in processed/ and the LESSONS tail is at the 20-block cap: the curator indexes
  (does not delete) and consolidates; nothing for lanes to do beyond writing once.
- The push (S8) happens before S9-S11 and is unaffected by memory work (curator edits stores only).
