project: Volitility-Model
role: domain-reviewer
task: REVIEW-B as-built domain review of REVIEW_A R1-R21 and lead R-1/R-2 against source, by reading and hand-derivation (no Bash)
deliverables: <REPO>/.claude/REVIEW_B.md
status: delivered
attestation: edited only .claude/REVIEW_B.md
source_judged: bs_pricing 12deadc4, data_io 3f0a1939, surface af6a5f38 (hub-stated); synthetic 1414ff07 (flow-lead-stated, re-read after notice; docstring-only change vs 73ee05b0 as read); viz.py, main.py, selftest.py unhashed (no Bash); hub to confirm with selftest.py --hashes
lesson: A control total asserted in the CALLER is a tautology when the caller defines the count as the very sum it then checks (main.py n_read = len(chain)+len(rejects), then assert n_read == len(chain)+len(rejects)); the independent counter must come from the producer's own tally (chain.attrs rows_read). Rule: for every printed control total, trace each side back to where it was first counted, and if both sides share one origin, the check is documentation. Second: a binding presentation ruling (R13) can be correct in code and still have no failing test when the only fixture never triggers its branch (clean chain keeps 0.8S in-domain); demand a fixture where the branch fires plus a mutation.
friction: Re-read synthetic.py after the flow-lead hash-change notice (necessary, disk state is authority, not a wasted lookup). Bash not granted, so flow-board.py --show/--note not run and no file hashes could be taken. SendMessage not granted, so findings are in REVIEW_B.md and the final report only. Advisor caught that I had not opened the LANE REVIEW-B block in SPAWN_PROMPTS.md before writing, and that the BUILD-B run-log R21(4) line should be verified; both done. No re-lookups of known info.
board_read: yes
