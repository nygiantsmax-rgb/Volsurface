project: Volitility-Model
role: domain-reviewer
task: REVIEW-B delta pass after R-9 fix round (D4/OX-2, D5, D1/D7, D3) on viz edc7196f, main 900228c8, selftest 34fbf338
deliverables: .claude/REVIEW_B.md section 5 (DELTA PASS 2026-11-02)
status: delivered
lesson: A mutation proof that takes "caught" from the mutated run's failed list instead of the failures that are NEW against the baseline, and never asserts the baseline was green, can report RED as required for a check that was already red; attribute RED only from new_red, and assert rc0 == 0 before trusting any mutation verdict. Separately, a display mask that borrows the nearest grid row's domain for an off-grid slice is a second definition of the domain, and a test pinned to an exact-grid slice (T_grid[0]) cannot see it diverge.
friction: Bash not granted, so flow-board.py --show/--note were not run and no hashes were taken (hub-stated hashes cited). Agent-memory files were listed but not opened, and the MEMORY.md index was used as given. Advisor caught three gaps before I wrote: D7's test half was missing, the mutation-proof attribution (D12), and OX-5 not being closable from an in-range q. No re-lookups of known info.
attestation: edited only .claude/REVIEW_B.md
board_read: yes
