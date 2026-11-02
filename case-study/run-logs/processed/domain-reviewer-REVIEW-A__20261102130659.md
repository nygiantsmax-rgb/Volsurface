project: Volitility-Model
role: domain-reviewer
task: REVIEW-A contract pass - rule on CONTRACT.md v1.0 treatment decisions (forward/dividend, OTM split, solver, total variance, diagnostics, fixed-strike mapping, RBF, SSVI truth, units)
deliverables: <REPO>/.claude/REVIEW_A.md
status: delivered
lesson: A domain flag defined against a UNION grid (in_domain = k_grid[0] <= k <= k_grid[-1]) is a label that cannot fail: it certifies per-maturity extrapolation as reliable. Hand-derive the per-slice data extent from the generator before accepting any "in range" flag, and define the domain once per slice, then make diagnostics, display and acceptance tests all point to that definition, with an anti-vacuity floor on n_checked so narrowing scope cannot produce a 0/0 pass. Separately, an absolute price tolerance in an IV solver gives a false converged status wherever price is comparable to tol; use relative residual.
friction: No Bash granted, so flow-board --show/--note could not run; read flow-board.md directly from disk and posted no note. SendMessage was not in the granted toolset, so CHANGE rulings could not be pushed live to the hub; relayed via REVIEW_A.md and the final report instead. No knowledge board exists for this project yet. No re-lookups of known info.
attestation: did not edit CONTRACT.md or any source
