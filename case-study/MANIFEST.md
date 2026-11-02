# Case-study manifest

This lists every published file in case-study/, with the sha256 of its source BEFORE redaction, every excluded item and why,
and the scan results. Redaction was applied to staging copies only, and the sources were hash-checked as unchanged.

## Published (source sha256 before redaction)

| Target | Source sha256 | Redactions |
|---|---|---|
| case-study/flow-artifacts/OWNERSHIP.md | 23818b5915b90b34 | home 10, identity 4, other_project 2, plan_file 1, repo 1 |
| case-study/flow-artifacts/SPAWN_PROMPTS.md | 6bce73f2d74116ee | home 69, plan_file 9, repo 33 |
| case-study/flow-artifacts/CONTRACT.md | d88f9e71e5e99eda | home 1, plan_file 1 |
| case-study/flow-artifacts/REVIEW_A.md | 5b2183ffacc845e5 | - |
| case-study/flow-artifacts/REVIEW_B.md | 22130c5fe7f7b2e8 | - |
| case-study/flow-artifacts/NEXT_STEPS.md | 4a1b8055405c106f | home 5, other_project 3 |
| case-study/flow-artifacts/NEXT_STEPS_MEMORY.md | 951395c961bf0cc9 | - |
| case-study/flow-artifacts/PAUSED_R9_TO_BLOCKS.md | cd034c4f9feeb42a | - |
| case-study/flow-artifacts/RETRO.md | f75f4521aed17ac0 | - |
| case-study/flow-artifacts/CASE_STUDY_PLAN.md | 5351e40f14d14296 | - |
| case-study/boards/flow-board.md | 52cda9c9f8da83ae | home 4, other_project 1, plan_file 1, repo 1, workflow_id 1 |
| case-study/boards/KNOWLEDGE_BOARD.md | 2eba302fa031619c | - |
| case-study/run-logs/memory-curator.md | c3051c731abd0aab | - |
| case-study/run-logs/processed/domain-reviewer-REVIEW-A__20261102130659.md | 0c2d7b9ac1c0660e | home 1, repo 1 |
| case-study/run-logs/processed/domain-reviewer-REVIEW-A__20261102130908.md | 919e7e1d97848f7f | home 1, repo 1 |
| case-study/run-logs/processed/domain-reviewer-REVIEW-B__20261102132331.md | 8bff55efed0327c2 | home 1, repo 1 |
| case-study/run-logs/processed/domain-reviewer-REVIEW-B__20261102143109.md | 8146f71956a8798f | - |
| case-study/run-logs/processed/flow-lead__20261102125409.md | 6a8b879a1e8ec73b | home 2, repo 2 |
| case-study/run-logs/processed/flow-lead__20261102130049.md | 54588642553486b7 | home 1, repo 1 |
| case-study/run-logs/processed/flow-lead__20261102133000.md | 8f1e1ee851c8a9cc | - |
| case-study/run-logs/processed/flow-lead__20261102150915.md | 97d54edf5a75c884 | - |
| case-study/run-logs/processed/handoff-documenter-HANDOFF__20261102143712.md | 884d8dddf57ebfc2 | home 1, identity 2, repo 1 |
| case-study/run-logs/processed/interface-designer-CONTRACT__20261102125748.md | 8b09d4dea061ea7c | home 1, repo 1 |
| case-study/run-logs/processed/main-session__20261102131701.md | 647e57a1f482eff0 | home 1 |
| case-study/run-logs/processed/memory-curator-midflow__20261102130402.md | 326aaa1457c84b92 | home 5 |
| case-study/run-logs/processed/memory-curator-midflow__20261102130639.md | 04b9a236dd289487 | home 5 |
| case-study/run-logs/processed/memory-curator-midflow__20261102131216.md | 61f118c2ea190919 | home 4 |
| case-study/run-logs/processed/memory-curator-plan__20261102133215.md | 790905a9eb339f27 | home 1, repo 1 |
| case-study/run-logs/processed/oracle-verifier-ORACLE__20261102131248.md | c38017a77b99648b | home 1, repo 1 |
| case-study/run-logs/processed/oracle-verifier-ORACLE__20261102131456.md | 0b59571f4dbc8a31 | home 1, repo 1 |
| case-study/run-logs/processed/oracle-verifier-ORACLE__20261102131831.md | c195b81a0accd1c8 | home 1, repo 1 |
| case-study/run-logs/processed/pipeline-builder-BUILD-A__20261102130639.md | db1385d4aba06338 | home 2, repo 2 |
| case-study/run-logs/processed/pipeline-builder-BUILD-A__20261102131237.md | 06c4d6e9404edec4 | home 2, repo 2 |
| case-study/run-logs/processed/pipeline-builder-BUILD-A__20261102131831.md | a3a341035df29ada | home 2, repo 2 |
| case-study/run-logs/processed/pipeline-builder-BUILD-B__20261102130553.md | e28fd8571793ee4f | home 2, repo 2 |
| case-study/run-logs/processed/pipeline-builder-BUILD-B__20261102131006.md | bf56e221e4f79b0c | home 2, repo 2 |
| case-study/run-logs/processed/pipeline-builder-BUILD-B__20261102131103.md | 2a699bec2f421619 | home 2, repo 2 |
| case-study/run-logs/processed/pipeline-builder-BUILD-B__20261102140357.md | cc0db0b2e8347599 | home 2, repo 2 |
| case-study/run-logs/processed/pipeline-builder-BUILD-C__20261102130627.md | 16e33b92838344c1 | home 3, repo 3 |
| case-study/run-logs/processed/pipeline-builder-BUILD-C__20261102131124.md | 3f3ac46ef4640433 | home 3, repo 3 |
| case-study/run-logs/processed/pipeline-builder-BUILD-C__20261102140408.md | 7376a08b52804afc | home 3, repo 3 |
| case-study/run-logs/processed/qa-verification-engineer-QA__20261102141312.md | be623f7b7c04fcd0 | home 1, repo 1 |
| case-study/agents/flow-lead.md | 916b6c226f2d4ac7 | home 3 |
| case-study/agents/interface-designer.md | b8abf56ab9fb3c47 | home 3 |
| case-study/agents/domain-reviewer.md | c796a9350549afad | home 3 |
| case-study/agents/pipeline-builder.md | 5b65150cda55778e | home 3 |
| case-study/agents/qa-verification-engineer.md | fd7b29da96d1353c | home 3 |
| case-study/agents/oracle-verifier.md | c31ac41098289326 | home 3 |
| case-study/agents/handoff-documenter.md | 61d2b00a16d39aaf | home 3 |
| case-study/agents/memory-curator.md | 518e0b8f8c3e4c6f | home 3 |
| case-study/agents/advisor.md | b4a72007b98aeb49 | home 3 |
| case-study/metrics/runs_table.csv, runs_table.md | derived from runs.jsonl (not published) | allowlist fields only |
| case-study/metrics/README.md, MANIFEST.md, INDEX.md, SHIP_RUNS.md | generated by the hub | - |

Post-scan staging edits (exact replacements, staging copy only):
- Rule text that quoted the home-path pattern was reworded to <home-dir> or <drive>--<home> (CASE_STUDY_PLAN, OWNERSHIP, SPAWN_PROMPTS).
- A price-tick constant written with a dollar sign was reworded (SPAWN_PROMPTS).
- User decision U-F(2): other-project incident details in agents/oracle-verifier.md, agents/domain-reviewer.md and
  agents/memory-curator.md were generalized. The live role files are unchanged. The domain-reviewer role description
  (accounting and financial-math scope) was kept, because it defines the role and is not another project's detail.
- CONTRACT.md has a 'superseded in part' header added (U-F(3)).

## Excluded (never copied, not even to staging)

| Item | Reason |
|---|---|
| agents/accuracy-first-scripter.md, big-picture-strategist.md, dependency-doctor.md, env-doctor.md | Never ran in this flow, so not pertinent to this project (U-F(1)) |
| team-memory agent-memory (all role craft files) | Iced by the user (U-E); contains other projects' material |
| team-memory LESSONS*, RESUME.md, HANDOFF.md, domains/ | Cross-project stores; strict isolation rule |
| team-memory state/, *.log, *.bak* (including the nudge-loop and monitor-config backups) | Machine state and duplicates |
| team-memory bin/ and config/ (hooks, judge prompt) | Hook machinery, not published this commit; metrics/README.md describes how scores were produced |
| Every other project's directory under team-memory/projects/ | Strict isolation rule |
| Raw runs.jsonl | Session and transcript identifiers and task text; published only as the derived table |
| The approved plan file under the Claude plans folder | A frozen input, not a flow artifact; references are redacted to <approved-plan>.md |
| vol_surface.html, scratchpad and staging directories | Generated output and temp files |

## Independent scan (PowerShell Select-String over the staging tree; separate tool from the Python redactor)

Hard classes (any hit blocks): home path in any form, the bare user-folder name, email, UUID, agent id, workflow id, secrets.
Final result: 0 hits in every hard class.
Soft classes (a hit holds the file): identity, machine name, cloud-sync folder name, dollar amounts, tickers,
financial-account terms, other-project names.
Final result: identity 0, machine 0, tickers 0, dollar 0, other-project 0 (case-sensitive where the class requires it).
Financial-account terms appear only in scan-rule text, in 'no employer identifiers' disclosure lines, and in the
domain-reviewer role description. Cloud-sync folder names appear only in rule text and in an excluded file's name.
Neither is data about a person or another project.
First-pass raw counts before the post-scan edits, case-insensitive: {"agent id": 0, "cloud folder": 5, "dollar": 1, "email": 0, "finance terms": 14, "home path": 3, "identity": 31, "machine": 0, "other project": 0, "secret": 0, "ticker": 8, "user folder": 0, "uuid": 0, "workflow id": 0}
