# Case study: building a volatility-surface tool with an AI agent team

This repo holds the code for a 3D implied-volatility surface tool. It also holds a record of how a team of AI agents built that code. The team ran hub-and-spoke: one coordinating session (the hub), a team lead (flow-lead) that made the rulings, a memory-curator that judged the work, and specialist roles that built and verified it.

The case study covers this project only. It contains nothing from other projects.

## In this commit
- `SHIP_RUNS.md` - the shipping gate. It records two clean live runs on byte-identical files, with exit codes, mutation-proof results and hash lists, all matching the code in this commit.

## Coming in a later commit
These are added after the team lead's retro and the memory-curator's final pass. That way they include the final rulings, the scoring and the knowledge board.
- **Routing:** the lane and ownership map and the spawn briefs for each role.
- **Agent decisions:** the rulings log (R-1 onward, with user decisions), the domain reviews of the contract and of the finished code, and the resume plans.
- **Scoring and metrics:** a table of per-agent run metrics and judge results, derived from the monitor's records. Identifiers and transcript text are removed.
- **Boards and run-logs:** the shared flow board, the project knowledge board, and each role's run-log.

## Sanitization
Every file published here is copied to a staging folder first and redacted there. Local machine paths become `<HOME>`, and session and transcript identifiers are removed. An independent scan then checks the staged copy for paths, emails, identifiers, secrets, personal data and other-project references. Because of the redaction, files are not byte-identical to the originals. The redaction changes only identifiers and paths, never the substance.
