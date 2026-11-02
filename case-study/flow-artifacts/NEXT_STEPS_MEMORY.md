# NEXT STEPS - memory-curator section (PLANNING ONLY, 2026-11-02)

Status: DRAFT plan for the terminal pass. No memory store was edited to produce it.
Merge target: flow-lead's plan. Sources read: LESSONS.md, domains/memory-system.md, KNOWLEDGE_BOARD.md,
flow-board.md, OWNERSHIP.md, processed/ run-logs (grep), rollup-runlog.ps1, inject-knowledge.py + its log,
monitor-config.json(+.bak-sr20), PAUSED_R9_TO_BLOCKS.md, own craft store.

Constraint on this role: no Bash. I cannot hash files or run scripts. Every hash is HUB-REPORTED and I
compare it to lane-reported hashes. I judge by Read/Grep of disk.

## 1. Judging plan (terminal pass)

Last-green hashes (PAUSED file): bs 12deadc4, syn 1414ff07, dio 3f0a1939, surf af6a5f38, viz b352af85,
main ac2ab824, self efd3db20. Rule: a hash a lane reports must equal the hub's post-fix hash, else the claim is stale.
Authoritative copy per lane = the LATEST file in processed/ (or inbox/ if present); earlier copies are superseded.

| Lane | State today | Evidence I will check |
|---|---|---|
| QA | no run-log yet; selftest.py was stopped mid-edit | run-log has attestation line "edited only selftest.py"; hub-reported selftest hash == QA-reported hash; Read selftest.py for D4 (R13 check can fail, with a named mutation + anti-vacuity), D3, D6, D10 text actually present; mutation was on scratch copy and live hash unchanged (QA states both hashes); pass count vs hub live run |
| ORACLE | latest copy 131831 has "attestation: edited only oracle_check.py" (copies 131248/131456 had long lines I did not open; treat 131831 as final) | order-of-events line (oracle written before built code read); hashes in log match hub; mutation FAIL count; noisy-chain minority count > 0; confirm post-fix rerun after BUILD fix round if flow-lead requires it |
| REVIEW-B | log 132331: attests only REVIEW_B.md; board_read: yes | attestation is INACCURATE-by-omission: R-9 records it also edited its own agent-memory (ruled benign, own craft store). Record as noted, not a violation. Check delta-pass report exists (D5, OX-2, R13 in viz.py) and that D9 concession is in REVIEW_B.md |
| BUILD-A | final copy 131831 attests; fix round gave BUILD-A no tasks | attestation present; hash bs/syn equals hub; R-2 guard line (vega<1e-8 -> Brent) quoted from bs_pricing.py by Grep |
| BUILD-B | final 131103 attests; R-9 fix round (D2, D8) owes a NEW run-log | new log: attestation, one write; Grep surface.py 211-214/355-357 comments say "structural check, main's recount is the gate"; Grep data_io.py ~290 docstring states R2 rule; code unchanged (hash of data_io equals 3f0a1939 unless docstring edit, then new hash stated) |
| BUILD-C | NO attestation in any processed copy (attested only in final report); R-9 owes new log | new log must carry attestation line; Grep main.py: params line printed first (D7), control total no longer self-sum (D1, or "n/a" wording); Grep viz.py: text says "gap" not "x markers" (D5); smile panel y=NaN where in_domain False (OX-2) with hub/QA proof NaN idx == in_domain False idx; hovertemplate/customdata untouched (R14) |
| HANDOFF | no run-log; no Bash | attestation "edited only README.md"; README states R-1/R-2 as governing 3.4 and says CONTRACT 3.4 price-only text is superseded; README lists open exceptions OX-1 (R14), OX-3, OX-4, OX-5, D9, and OX-2 if not landed; every command in README appears in main.py argparse or a lane run-log (Grep each) |
| flow-lead (retro) | not a listed lane but owns restore | Grep sample_rate in monitor-config.json == 20 (first act of my pass) |

Judge outputs: per lane one of attested-and-verified / attested-unverified / no-attestation / mismatch, with the file+line.
A missing attestation line is the detector (OWNERSHIP verifier-separation rule); I flag, I do not scold.

## 2. Routing plan (nothing written yet; stores read)

Dedup key = name field + content, not filename (feedback_dedup_by_identity_not_path.md). My own store has 1 file, no overlap with below.

| # | Candidate takeaway | Destination | Dedup note | new/updated |
|---|---|---|---|---|
| 1 | Nudge/monitor hook that feeds back into the scored agent needs an idempotency key (agent_id, flag set); prove with two-stop replay | LESSONS head (one line) | Already in LESSONS TAIL (main-session 2026-11-02), which is NOT injected and will roll off at the cap; promote to head, then the tail copy may drop. Evidence (backup name, replay) goes to domains/memory-system.md | updated |
| 2 | Judge-rate restore must be enforced by something that runs | domains/memory-system.md | Section "An owed restore of GLOBAL config" already exists; UPDATE status (restored? by what?) and add the chosen enforcer. Head already has the doctrine line? No: only the tail has it. Add one sentence to head only if user picks the script | updated |
| 3 | Tools frontmatter: spokes DID get SendMessage in this very spawn (my toolset = frontmatter line exactly: Read,Grep,Glob,Write,Edit,SendMessage; Bash absent; advisor present though unlisted) | domains/memory-system.md (new section "tools: edit took effect after reload/respawn, evidence") and amend LESSONS head tools bullet by half a sentence | LESSONS head already says the tools list is an allowlist hint and Edit leaks; this adds the opposite direction (an added tool can arrive) and that the probe lacking it earlier was a stale-session effect | updated |
| 4 | SendMessage on spokes conflicts with the hub-and-spoke ruling: frontmatter cannot limit the `to` target | LESSONS head (extend the existing hub-and-spoke bullet by one sentence) + domains/memory-system.md | Bullet exists (user ruling 2026-11-02); extend, do not duplicate | updated |
| 5 | Rollup appends one board/LESSONS block per run-log VERSION; write-once rule (R-8) is only a reminder | domains/memory-system.md (new section with the tail evidence: oracle-verifier x3, domain-reviewer x2, memory-curator x3 in LESSONS tail) | Board already has a Harness-facts bullet; keep that bullet, add pointer. Fix proposal is user decision D below | new section |
| 6 | LESSONS tail is AT the 20-block cap, so each new lesson-bearing run-log evicts a real older one; duplicates burn the budget | domains/memory-system.md | not stated anywhere today | new |
| 7 | Verifier on a live tree: snapshot to scratch, hash, then rerun live; label checks must be re-run on a fixture where they flip | agent-memory/oracle-verifier/pattern_live_tree_snapshot_and_flip_fixture.md | The lesson appears 3x in LESSONS tail (not a store). Read oracle-verifier store content first; if an existing pattern covers vacuous-fixture, UPDATE it and add the snapshot rule | new or updated after reading |
| 8 | Union-grid in_domain flag cannot fail; define domain per slice once; vol-space convergence beats price-space (R-1 beat reviewer's relative-price rule); control total computed in caller is a tautology; ruling can be correct yet untested when fixture never triggers branch | agent-memory/domain-reviewer/ (pattern_flag_that_cannot_fail.md) | Likely partly covered by domain-reviewer's 6 existing files; read bodies, merge into the nearest | updated preferred |
| 9 | Broadcast ALL args together (flag arg dropped by broadcast_to); read upstream module before writing a stub; heredoc/s.index slip pattern; plotly 7 to_dict base64 | agent-memory/pipeline-builder/ (update pattern_pipeline_gate_and_idempotency.md or new pattern_numpy_broadcast_and_stubs.md); plotly fact is project fact -> board (already there) | s.index uniqueness already in LESSONS head dated 2026-10-01, do NOT re-add | updated |
| 10 | Check each role's tools: before planning verification; no-Bash roles cannot run commands | agent-memory/flow-lead/ (feedback_check_tools_before_planning.md) | LESSONS tail has it; board has the Bash/no-Bash fact. Role craft, not universal | new after reading flow-lead store |
| 11 | Mid-flow batch->live switch makes a precondition lane concurrent; late ruling lands after code | agent-memory/flow-lead/ | same store as 10; merge into one file if bodies adjoin | new/merged |
| 12 | Phase-0 pinned vocabulary + omit boolean ok keys from diagnostic formats | agent-memory/interface-designer/ | read store; probably extends an existing contract-pinning pattern | updated |
| 13 | Judge/curator craft: run-logs must carry an attestation line or the lane is unjudgeable; judge by Grep on disk; no Bash means hash comparison is hub-supplied | agent-memory/memory-curator/pattern_judging_attestations.md | own store has only the dedup feedback; no overlap | new |
| 14 | Project facts: IV acceptance, in_domain R9-R11, plotly 7, q guard, env, harness facts | KNOWLEDGE_BOARD curated sections | ALREADY there; only add: R-9 outcomes (what landed, final hashes, README open exceptions) after HANDOFF, and flip the "Open obligations" entry | updated |
| 15 | MAX_CHARS=6000 in inject-knowledge.py truncates the board injection, curated head first; board is near/over that, so tail facts and Open obligations may never be injected | domains/memory-system.md + keep board head under ~5000 chars (curate; move evidence to a second file `facts-detail.md`? NOTE: the hook injects every *.md in knowledge/, so a second file competes for the same 6000) | new | new |

Do NOT file: per-defect fix recipes (D1-D11), hashes, 108/37 counts (ephemeral, in REVIEW_B.md / run-logs).
Do not file anything before flow-lead's retro (it produces takeaways). Cap each store index near 25; the stores touched likely stay well under.

## 3. Board hygiene

Duplicate-block problem
- Root cause (read in rollup-runlog.ps1 lines 43-60): one block appended per run-log file seen, no identity check; run-logs get rewritten after rollup moved the first copy, and the LESSONS tail has the same defect (not only the board).
- Process fix already ruled (R-8, write once) is a reminder only. Real fix is MACHINERY: in rollup-runlog.ps1, before Add-Content, compute a hash of (project|role|lesson text) and skip when the target already contains the exact "lesson: <text>" line. Proposed as user decision D4 below.
- Interim: curator consolidates tail blocks at terminal pass (as done for 5 BUILD-B blocks); each new lesson-bearing log evicts one block since LESSONS tail is already at cap 20.
- Do not use the `domain:` line for facts (block carries lesson+friction only). Curate facts into the sections above the marker.

processed/ duplicates (7 lanes have more than one copy: flow-lead x2, REVIEW-A x2, memory-curator-midflow x3, BUILD-A x2, BUILD-B x3, BUILD-C x2, ORACLE x3)
- Do NOT delete. They are evidence, I have no delete tool, and the rollup does not read processed/.
- Make an index instead: one table in domains/memory-system.md or a processed/INDEX.md (a non-run-log file; rollup only scans inbox/ root, and the processed/ subfolder is excluded) naming per lane the authoritative (latest) copy and the superseded ones. Judging cites the authoritative copy.
- If the user later wants disk cleanup: move superseded copies to processed/superseded/ with a script, keeping the latest per lane; never delete.

Open question: do subagents receive SessionStart injection?
- Evidence on disk: inject-knowledge.log shows 116 "-> Volitility-Model" firings, many within seconds of each other at 13:04, so the hook fires per spawn (source=startup). It does NOT record who it fired for, and not that the context reached the agent.
- Evidence in this spawn: my initial prompt contained no "Project knowledge auto-loaded" block and no LESSONS doctrine block (the system prompt did, via the role file's inlined text only). That is strong evidence the additionalContext is NOT delivered to subagents, but one observation, not proof.
- Settling test (cheap): put a CANARY line in the FIRST 500 chars of KNOWLEDGE_BOARD.md (e.g. "CANARY-<nonce>"), spawn one fresh role with the instruction "before any tool call, state the canary if you know it, else say NONE", then check the transcript for a Read of KNOWLEDGE_BOARD.md. Canary known with no Read = injection works; NONE then Read = read-path is only startup-block item 3. Remove the canary after. Run it on the spawn after a session reload.
- If injection does not reach subagents, the 6000-char cap is moot for them and the startup block item 3 is the only read path; then board_read: yes/no in every run-log is the monitor (REVIEW-B is the only lane attesting so far; earlier lanes predate the board).

## 4. Decisions needed from the USER (recommendations)

D1. Keep the ", SendMessage" tools edit?
- New evidence: this spawn WAS granted SendMessage (toolset equals the edited frontmatter: Read, Grep, Glob, Write, Edit, SendMessage; no Bash), so the edit appears to have taken effect after the earlier probe, probably a session reload or fresh agent load. Not yet proven end to end.
- Cost: it enables spoke-to-spoke messages, which the hub-and-spoke ruling forbids, and frontmatter cannot restrict the `to` field.
- Recommend: KEEP, but only with a guard: (a) every spoke brief states "to: main only"; (b) score-subagent.py flags any SendMessage call whose target is not "main" (needs a transcript scan, a small change); (c) test after reload with a nonce: hub spawns one spoke, spoke sends "NONCE-<n>" to main, hub confirms receipt and that the spoke has no Bash/Edit beyond its line. If (b) is not wanted, revert from the backup in ~/.claude/agents-backup-20261102-sendmessage/.
D2. Make the judge-rate restore enforced by a script?
- Recommend: YES, as a CHECK not a silent auto-restore: at flow start (SessionStart hook or flow-lead's first step) diff monitor-config.json against .bak-sr20 and print a loud mismatch. A silent restore would clobber a deliberate rate-1 flow. For THIS flow: restore stays flow-lead's last act, and my terminal pass starts by Grep-verifying sample_rate == 20 (currently 1).
D3. Should the nudge fix also suppress the per-stop LLM judge re-run?
- runs.jsonl has 114 lines for this project, 17 for memory-curator, so re-judging cost is real at sample_rate 1.
- Recommend: YES, narrowly: key the judge on (agent_id, transcript length or hash) so UNCHANGED evidence is not re-judged; new evidence is still judged. Do not suppress judging outright.
D4. (added) Dedup in rollup-runlog.ps1 (skip a block whose lesson text already exists in the target)?
- Recommend: YES. Small, deterministic, fixes the board and the LESSONS tail, and frees the 20-block cap. Back up the script first, prove with a two-append replay (second must be a no-op), same method as the nudge fix.
D5. (added) Raise or restructure inject-knowledge.py MAX_CHARS=6000 handling?
- Recommend: keep 6000; curate the board head under it and verify by character count after the terminal pass. No code change unless D1-canary shows injection reaches subagents.

## 5. Order of my terminal-pass steps vs flow-lead's retro

1. (before me) flow-lead retro, then flow-lead restores judge rate (my step 2 verifies it).
2. Verify: Grep sample_rate in monitor-config.json == 20. If not, report and continue; do not restore myself (not my file, no Bash).
3. Obtain hub-reported final hashes and the QA/BUILD/HANDOFF final run-logs; judge per Section 1 using the latest copy per lane.
4. Read retro takeaways (flow-lead run-log) and every target store's existing files (name + content) before writing.
5. Route per Section 2: dedup first, update-over-add, index lines appended not overwritten.
6. Board: curate facts above the marker, fold R-9 outcomes and README open exceptions, mark open obligations closed, consolidate duplicate tail blocks, check head under ~5000 chars; write processed/ INDEX.
7. Prune pass on each touched store; machinery results (D1-D4) recorded in domains/memory-system.md.
8. Run-log written ONCE (no rewrite), with an attestation line and board_read line; no domain: line unless a project fact.
Then: hub live runs n+1, push to GitHub (hub's step, not mine).
