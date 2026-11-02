# CASE_STUDY_PLAN - second commit, case-study/ (flow-lead, 2026-11-02)

Status: PLAN for the hub to execute AFTER the S11 curator pass. Scope: THIS PROJECT ONLY (U-E): routing, agent decisions and
rulings, scoring and metrics. Authority: OWNERSHIP.md corrections log U-D, R-10, R-11, U-E. Nothing here is executed by flow-lead.
This file is itself published, so it names scan CLASSES with placeholders; the literal term list lives in the hub's scratch script,
outside the repo (R-11).

## 1. Execution order (hub, transport only)
1. Copy every source below into a STAGING dir outside the repo (a fresh empty dir). Hash every source first.
2. Redact the staging COPY only (section 6). Never edit a source.
3. Re-hash the sources: must equal step 1.
4. Run the independent scan (section 7) with a DIFFERENT tool than the redactor (plain grep). A hit in a hard class blocks;
   a hit in a soft class HOLDS for the user (R-10(e)); a held file defaults to EXCLUDED and is listed in case-study/MANIFEST.md.
5. Derive the runs table (section 4). Write MANIFEST.md and the INDEX.md delta (section 8).
6. Copy staging into the repo's case-study/, commit, push normally.
7. Gates: sources hash-unchanged; git ls-files case-study equals the manifest exactly; fresh clone holds the manifest files.

## 2. Publish list (source -> target). <CLAUDE> is the repo's .claude/ folder; <TM> is team-memory/projects/Volitility-Model/

### 2a. Flow artifacts (this project only)
| Source | Target |
|---|---|
| <CLAUDE>/OWNERSHIP.md | case-study/flow-artifacts/OWNERSHIP.md |
| <CLAUDE>/SPAWN_PROMPTS.md | case-study/flow-artifacts/SPAWN_PROMPTS.md |
| <CLAUDE>/CONTRACT.md | case-study/flow-artifacts/CONTRACT.md (header added by hub: "v1.0, superseded in part by OWNERSHIP R-1..R-9 and REVIEW_A") |
| <CLAUDE>/REVIEW_A.md | case-study/flow-artifacts/REVIEW_A.md |
| <CLAUDE>/REVIEW_B.md | case-study/flow-artifacts/REVIEW_B.md |
| <CLAUDE>/NEXT_STEPS.md | case-study/flow-artifacts/NEXT_STEPS.md |
| <CLAUDE>/NEXT_STEPS_MEMORY.md | case-study/flow-artifacts/NEXT_STEPS_MEMORY.md |
| <CLAUDE>/PAUSED_R9_TO_BLOCKS.md | case-study/flow-artifacts/PAUSED_R9_TO_BLOCKS.md |
| <CLAUDE>/RETRO.md | case-study/flow-artifacts/RETRO.md |
| <CLAUDE>/CASE_STUDY_PLAN.md | case-study/flow-artifacts/CASE_STUDY_PLAN.md |

Note: CONTRACT.md was withheld from commit 1 (U-B) and is stale against the rulings; U-D/U-E now put it in scope. It carries a local
path on its line 4 (redacted by section 6). Reason for the header: the pushed text must not contradict the code without saying so.

### 2b. Boards (Volitility-Model only)
| Source | Target |
|---|---|
| <TM>/flow-board.md | case-study/boards/flow-board.md |
| <TM>/knowledge/KNOWLEDGE_BOARD.md | case-study/boards/KNOWLEDGE_BOARD.md (as curated by S11) |

### 2c. Run-logs (this project only)
Rule: every file matching <TM>/inbox/processed/*.md and <TM>/inbox/*.md at execution time, target case-study/run-logs/<same file name>
(processed ones under case-study/run-logs/processed/). At planning time there are 28 processed files and the inbox holds none; the
inbox will gain the flow-lead and memory-curator logs (written after this plan) and these are admitted by the same rule. Keep
duplicate versions (they are evidence of the write-once defect, RETRO section e). The "other-project" rule (section 5) applies.

### 2d. Routing: agent role definitions
| Source | Target |
|---|---|
| ~/.claude/agents/flow-lead.md | case-study/agents/flow-lead.md |
| ~/.claude/agents/interface-designer.md | case-study/agents/interface-designer.md |
| ~/.claude/agents/domain-reviewer.md | case-study/agents/domain-reviewer.md |
| ~/.claude/agents/pipeline-builder.md | case-study/agents/pipeline-builder.md |
| ~/.claude/agents/qa-verification-engineer.md | case-study/agents/qa-verification-engineer.md |
| ~/.claude/agents/oracle-verifier.md | case-study/agents/oracle-verifier.md |
| ~/.claude/agents/handoff-documenter.md | case-study/agents/handoff-documenter.md |
| ~/.claude/agents/memory-curator.md | case-study/agents/memory-curator.md |
| ~/.claude/agents/advisor.md | case-study/agents/advisor.md |

DEFAULT-EXCLUDED, listed in MANIFEST.md, USER choice: accuracy-first-scripter.md, big-picture-strategist.md, dependency-doctor.md,
env-doctor.md. They never ran in this flow, so they are not pertinent to this project (U-E). Excluding them is a scope narrowing and
is therefore stated, not silent.
Expected SOFT hits in the included role files (hold for the user, R-10(e)); pre-listed so the hub is not surprised:
oracle-verifier.md line 4 and lines 33-35 (spreadsheet/penny-parity incident text), domain-reviewer.md line 35 (employer/ledger
identifiers wording), memory-curator.md line 19 (finance routing wording). Each is generic role text, not a person or an employer;
the user decides keep or edit-the-staging-copy. All role files also carry a hard-coded home path in the flow-board and run-log lines;
section 6 redacts it.

### 2e. Derived runs table
| Source | Target |
|---|---|
| <TM>/runs.jsonl (never copied) | case-study/metrics/runs_table.md plus case-study/metrics/runs_table.csv |

## 3. Generated, not copied
case-study/INDEX.md (updated, section 8), case-study/MANIFEST.md (section 8), case-study/metrics/README (provenance, section 4).
case-study/SHIP_RUNS.md already exists from commit 1 and is unchanged.

## 4. Derived runs table specification
Allowlisted fields ONLY, one output row per runs.jsonl row, in file order:
agent_type, ts, out_tokens, tool_uses, duration_s, det_flags (joined with "|"), nudged (true/false/blank when absent), judge_on_task,
judge_pertinent (booleans; blank when the row has no judge).
Derived helper columns (not copied from any field): row (1..N) and agent_ordinal (A01, A02, ... assigned in first-appearance order of
agent_id, so rows of one agent can be grouped without publishing the id). The ordinal is a hub-side pseudonym; the id-to-ordinal map
is NOT written anywhere.
DROPPED unconditionally: session_id, agent_id, transcript, task, any judge key other than the two booleans (rationale in particular),
project, peak_context, tool_histogram, friction_selfreport, selfreport_miss, tier. No other field is admitted without a ruling.
Header paragraph the hub must write above the table (provenance): rows are CUMULATIVE SubagentStop snapshots, not one row per spawn;
about 100 of 160 rows carry agent_type "(unknown)" and some exactly duplicate a typed row (a monitor attribution defect, RETRO
section e); agent identity was dropped by rule; judging was by a haiku-class model at sample_rate 1 during the flow; det_flags and
judge booleans are monitor outputs, not ground truth; the `nudged` column exists only after the nudge-loop fix (13:14) and is blank
before it. The table states how the scores were produced; bin/ and config/ are not published (section 6).
Acceptance checks: row count equals runs.jsonl line count; column set equals the allowlist plus the two helper columns; a grep of the
output for a UUID, an agent-id pattern, "rationale", "transcript" and "task" returns nothing.

## 5. Rule for any line that names another project
Applies to EVERY file class (boards, flow artifacts, run-logs, role files), not only run-logs. A line that names another project:
replace the name with "<other-project>", or drop the line if the sentence cannot be read without it. NEVER publish it. The
other-project names are enumerated at execution time from the directory listing of team-memory/projects/ (all entries except
Volitility-Model) and from the existing board text; do not hand-type them into any published file.
Pre-found hits at planning time (hub to confirm by grep, not by trusting this list): KNOWLEDGE_BOARD.md line 62; flow-board.md
line 9; NEXT_STEPS.md around line 211; OWNERSHIP.md R-10(f) text and R-11 lines. Also the batch-workflow id on both boards
(section 6). Preferred redaction: the sentence keeps its meaning ("left over from another project's flow").

## 6. Redaction rules (staging copy only; apply in this order)
1. Home path: every form of the user's home directory to <HOME>: forward-slash, backslash, doubled-backslash (escaped), URL-encoded,
   the Claude project-slug form (drive plus dashes plus the user folder name, for example the "<drive>--<home>-..." style), ~ expansions
   of the config directory, and USERPROFILE / expanduser references. Result must read naturally, e.g. <HOME>/.claude/agents.
2. Session and agent identity: drop the UUID pattern (8-4-4-4-12 hex, case-insensitive); drop agent ids matching a[0-9a-f]{16}; drop
   the batch-workflow id (the "wf_" form, which appears on both boards); drop transcript file names.
3. Do NOT apply a generic long-hex rule: the sha256 prefixes and full digests in the run-logs are evidence and must survive.
4. Email address and the user's real name and university identity: remove or replace with "<user>" (the literal strings are in the
   hub's scratch scan list, not here). The public repo owner login is the single allowed handle.
5. Other-project names: section 5.
6. Non-ASCII: fold to ASCII by MAPPING (em dash and en dash to "-", curly quotes to straight), never by stripping.
7. Preserve line structure; no other edits. INDEX.md says what was changed (home path, ids, other-project names, held files, derived
   table), NOT "unedited" (R-11).

## 7. Independent scan classes (plain grep over the staging tree, run by a different tool than the redactor)
Hard classes (any hit blocks the commit): home path in any form; the bare user-folder name, case-insensitive (catch-all, finds forms
not listed above such as the slug form); email address; UUID; agent-id pattern; workflow id; secrets and tokens (github token
prefixes, "sk-" followed by 20 or more key characters, AKIA, bearer, api_key, password; allow-list only the repo owner login).
Soft classes (hit HOLDS the file for the user): personal name or handle other than the repo owner; the university identity;
machine name; dollar amounts; ticker symbols (the earlier user clearance covered main.py and selftest.py ONLY, so any ticker hit in a
case-study file holds); account, broker, cost-basis, employer, ledger, spreadsheet-workbook terms; other-project names (should be 0
after section 5); digit runs of 4 or more (spot check). The two benign constants already cleared in commit 1 (the tick-size constant
and the ASCII dash-folding helper) are cleared in the code only, not in case-study text.
Positive checks: no .pyc, no *.bak*, no .gitignore-excluded file in the manifest.

## 8. INDEX.md delta and MANIFEST.md
INDEX.md (flow-lead owns the text; hub applies): replace its "not yet published" wording (if any) with a short section "Second
commit" stating: contents (flow artifacts, boards, run-logs, role definitions, derived runs table); the redaction method in section 6
(what changed); that paths inside the files do not exist in the repo; that the CONTRACT is v1.0 superseded in part by the rulings;
that held or excluded files are named in MANIFEST.md; that agent-memory craft files, LESSONS, raw runs.jsonl, bin/ and config/ are
NOT published and why (iced by the user, other projects' material, session identifiers, hook machinery).
MANIFEST.md lists: every published file (target path and source sha256 of the pre-redaction source), every EXCLUDED item with the
reason (the four non-pertinent role files, any held file with file:line and class, agent-memory, LESSONS*, RESUME.md, HANDOFF.md,
state/, *.log, *.bak*, bin/, config/, other projects' directories, raw runs.jsonl), and the scan result counts per class.

## 9. EXPLICIT EXCLUDE list (never copied, not even to staging)
agent-memory (all, iced by U-E); LESSONS* ; RESUME.md ; HANDOFF.md ; state/ ; *.log ; *.bak* (including the nudge-loop backup and the
monitor-config backup) ; bin/ ; config/ ; every other project's directory ; raw runs.jsonl ; the plan file under ~/.claude/plans (a
frozen given, not a flow artifact); vol_surface.html ; scratchpad and staging dirs.

ANSWERED (user decisions U-F, OWNERSHIP corrections log): (1) four non-pertinent role files EXCLUDED; (2) the three soft-hit role files GENERALIZED in the staging copy only (other-project details to <other-project>, live files unchanged); (3) CONTRACT.md with header ACCEPTED; (4) other-project names redacted ACCEPTED; (5) agent_ordinal column ACCEPTED; role-file and SPAWN_PROMPTS edits NOT NOW (proposals only). The text below is the original question list, kept for the record.

Needs the USER before execution (defaults in force): (1) the four non-pertinent role files, default excluded; (2) the soft-class role
text hits in section 2d, default HOLD until the user says keep or edit; (3) CONTRACT.md in with a "superseded in part" header
(default yes, per U-D/U-E); (4) other-project names in boards: default redact to "<other-project>"; (5) the derived runs table with
the agent_ordinal helper column (default yes; drop it if the user wants no per-agent grouping).
