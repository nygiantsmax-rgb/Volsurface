project: Volitility-Model
role: pipeline-builder
task: BUILD-B lane - data_io.py and surface.py; CONTRACT v1.0, REVIEW_A fix round (R2, R9, R10, R11, R21), fix round R-9 (D2, D8)
deliverables: <REPO>/data_io.py, <REPO>/surface.py
status: delivered
r21_1: K_GRID_MODE default "union"; "intersection" only a non-default internal option, not a CLI flag
r21_2: R9 implemented as written; Surface fields k_lo (n_T,), k_hi (n_T,), in_domain (n_T, n_k) bool, after K and before method
r21_3: R10 term_structure in_domain uses k_lo/k_hi; R11 a-d with in-domain-only n_checked and exact R11(c) disclaimer
r21_4: clean chain spline in-domain butterfly 0/4348 (prediction held); rbf 0/4348; calendar 0/4389 both
r21_5: 56 extrapolated-node butterfly violations, excluded by R11 scope (spline, clean chain, full grid 56/4680); spline not tuned
n_checked_before_after_clean: calendar 4720 -> 4389; butterfly 4680 -> 4348
r9_D2: surface.py comments/docstrings relabelled: OTM-count test is skipped by the flag it polices and the n_quotes_used test is an identity; both labelled STRUCTURAL CHECK, main's own recount is the gate. No logic added.
r9_D8: data_io.py fetch_yfinance_chain docstring corrected to the R2 rule; code unchanged.
self_checks: PowerShell $LASTEXITCODE: python -W error data_io.py = 0; python -W error surface.py = 0
sha256: data_io.py 589F5C78415BCF97D216B88CEAAC449128E425C5DFC3FE2C72509F0C645B6BF9; surface.py BE111B3EDCC0E61C1A357A3D64E6EBB35EC75916949782CA9D116E8ECA576BEC
board_read: yes
lesson: A check whose guard is the flag it polices, or whose two sides share one mask, is a structural check and must be labelled so at the site; naming the real gate beats leaving a "control total" comment that claims more than it does. A narrowed-scope diagnostic needs two anti-vacuity injections (in-domain counts, extrapolated does not).
domain: Volitility-Model - spline full-grid butterfly violations sit at extrapolated left-edge nodes (k about -0.56..-0.54, short T) from flat clamp plus PCHIP in T; R11 scope excludes them.
friction: first flow-board --show used a backslash path and failed (known from own agent-memory), redone with forward slashes. SendMessage unavailable. One own-test error earlier (clean-chain K=80 assumed out of domain). Docstring/code contradiction D8 was my own stale text left after the R2 edit.
stubs_left: none
attestation: edited only data_io.py and surface.py (plus this run-log); did not edit other lanes' files
