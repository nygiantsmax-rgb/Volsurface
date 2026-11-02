project: Volitility-Model
role: domain-reviewer
task: REVIEW-A contract pass - rule on CONTRACT.md v1.0 treatment decisions (forward/dividend, OTM split, solver, total variance, diagnostics, fixed-strike mapping, RBF, SSVI truth, units); plus relayed BUILD-B spline-edge finding (R21) and lead overrule R-1 on IV acceptance (R5 conceded)
deliverables: <REPO>/.claude/REVIEW_A.md
status: delivered
lesson: A domain flag defined against a UNION grid (in_domain = k_grid[0] <= k <= k_grid[-1]) is a label that cannot fail: it certifies per-maturity extrapolation as reliable. Define the domain once per slice, point diagnostics, display and acceptance tests at that one definition, and add an anti-vacuity floor on n_checked so narrowing scope cannot yield a 0/0 pass. Builder-reported diagnostic violations at grid edges should first be located against the per-slice data extent before anyone trims the grid to hide them. For IV solvers, accept convergence in vol space (|resid/vega|), not price space; the lead's R-1 beat my relative-price rule because it bounds the quantity the test checks.
friction: No Bash granted, so flow-board --show/--note could not run; read flow-board.md directly and posted no note. SendMessage not in granted toolset, so CHANGE rulings could not be pushed live; builds finished before REVIEW_A.md landed, so every CHANGE is now fix-in-place (cost of running review concurrently with builds). No knowledge board exists yet. No re-lookups of known info.
overrule: lead R-1 (vol-step acceptance) superseded my R5; I think the overrule was right and better than my position.
attestation: did not edit CONTRACT.md or any source
