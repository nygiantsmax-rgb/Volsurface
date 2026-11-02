project: Volitility-Model
role: memory-curator
task: mid-flow filing of 5 takeaways plus answer to "how is the knowledge board being used" (evidence from disk)
deliverables: <HOME>/.claude/team-memory/LESSONS.md (head, 2 bullets refined), <HOME>/.claude/agent-memory/flow-lead/pattern_orchestration_practice.md, <HOME>/.claude/agent-memory/flow-lead/MEMORY.md, <HOME>/.claude/team-memory/domains/memory-system.md, <HOME>/.claude/team-memory/projects/Volitility-Model/knowledge/KNOWLEDGE_BOARD.md
status: delivered
lesson: Board read-path usage is unproven until a run-log records it: two reports said the board was missing, none reported reading it, and the write path (domain: line, Stop hook rollup-runlog.ps1) fired once for BUILD-B. Settle subagent injection by a post-board spawn that must quote a board-only fact and show whether a Read call occurred, or by requiring a board_read yes/no run-log line.
friction: Bash not granted, so flow-board --show/--note not run (read flow-board.md from disk, no notes posted). Confirmed repeat-search: after a Grep -n of settings.json already returned the hook commands and line numbers, I Read the same file again; the Read added nothing. Rule: when Grep -n returns the lines needed, do not Read to confirm. One no-op Edit issued earlier (rejected). Did not call advisor. Rollup moved my first run-log to processed/, so this one was rewritten fresh.
