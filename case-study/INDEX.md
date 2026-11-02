# Case study: building a volatility-surface tool with an AI agent team

This repo holds the code for a 3D implied-volatility surface tool. It also holds a record of how a team of AI agents built that code. The team ran hub-and-spoke: one coordinating session (the hub), a team lead (flow-lead) that made the rulings, a memory-curator that judged the work, and specialist roles that built and verified it.

The case study covers this project only. It contains nothing from other projects.

## First commit (code push)
- `SHIP_RUNS.md` - the shipping gate. It records two clean live runs on byte-identical files, with exit codes, mutation-proof results and hash lists, all matching the pushed code.

## Second commit (now published)
Added after the team lead's retro and the memory-curator's final pass, so they include the final rulings, the scoring and the knowledge board.
- **Routing:** the lane and ownership map and the spawn briefs for each role.
- **Agent decisions:** the rulings log (R-1 onward, with user decisions), the domain reviews of the contract and of the finished code, and the resume plans.
- **Scoring and metrics:** a table of per-agent run metrics and judge results, derived from the monitor's records. Identifiers and transcript text are removed.
- **Boards and run-logs:** the shared flow board, the project knowledge board, and each role's run-log.

## Sanitization
Every file published here is copied to a staging folder first and redacted there. Local machine paths become `<HOME>`, and session and transcript identifiers are removed. An independent scan then checks the staged copy for paths, emails, identifiers, secrets, personal data and other-project references. Because of the redaction, files are not byte-identical to the originals. The redaction changes only identifiers and paths, never the substance.

## Where things are (second commit)
- `flow-artifacts/`:
  - The routing: OWNERSHIP.md (lane map, model plan, corrections log R-1 onward, user decisions U-A onward) and SPAWN_PROMPTS.md.
  - The decisions: CONTRACT.md (v1.0, superseded in part by the rulings; see its header), REVIEW_A.md and REVIEW_B.md (domain rulings and the as-built review).
  - The plans: NEXT_STEPS.md, NEXT_STEPS_MEMORY.md and PAUSED_R9_TO_BLOCKS.md.
  - RETRO.md (timeline, defects with root causes, model-plan check, metrics, proposed prompt edits) and CASE_STUDY_PLAN.md (how this folder was built).
- `boards/`:
  - flow-board.md, the live shared scratchpad that agents read and wrote during the flow.
  - KNOWLEDGE_BOARD.md, the curated project facts injected into new sessions.
- `run-logs/`: every role's run-log, including duplicate versions, kept as evidence of the write-once defect.
- `agents/`: the role definitions (prompts) of the roles that ran in this flow.
- `metrics/`: the derived monitor table (per-agent tokens, tool use, flags, judge booleans) and its provenance.
- `MANIFEST.md`: every published file with its pre-redaction source hash, everything excluded and why, and the scan results.
- `SHIP_RUNS.md`: the shipping gate for the code commit.

Paths inside these files (for example <HOME>/... or <REPO>/...) refer to the original working machine and do not exist in this
repo. Agent-memory craft files, cross-project lesson stores, the raw monitor log and the hook machinery are not published.
MANIFEST.md says why.
