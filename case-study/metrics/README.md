# Metrics provenance

`runs_table.csv` and `runs_table.md` come from the team-memory monitor's `runs.jsonl` for this project. A hook
(`score-subagent.py`, not published) appends one record each time a subagent stops. The raw file is not published.

How the table was made:
- One output row per monitor record, in file order. It has 164 rows from 164 records.
- The rows are cumulative SubagentStop snapshots, not one row per spawn. One agent stopping several times produces several rows.
- About 100 rows have agent_type "(unknown)", and some duplicate a typed row. This is a monitor attribution defect,
  recorded in the case-study RETRO.
- Fields kept: agent_type, ts, out_tokens, tool_uses, duration_s, det_flags, nudged, and the two judge booleans
  judge_on_task and judge_pertinent.
- Fields dropped: session_id, agent_id, transcript, task, the judge rationale, project, peak_context,
  tool_histogram, friction_selfreport, selfreport_miss and tier.
- agent_ordinal (A01, A02, ...) is a pseudonym assigned in first-appearance order. The id-to-ordinal map was never written.
  There are 119 distinct ordinals, including the snapshot duplicates.
- det_flags are deterministic monitor flags (for example repeat-search). The judge booleans come from a small (haiku-class)
  LLM judge, run at sample_rate 1 during this flow and restored to 20 at the end.
  Both are monitor outputs, not ground truth.
- `nudged` exists only after the nudge-loop fix at 13:14 on 2026-11-02, so the column is blank before that.
  The fix made the monitor's re-wake message idempotent per agent and flag set.
