project: Volitility-Model
role: qa-verification-engineer
task: selftest.py (38 content checks + mutation proof) for the vol-surface build, fix round R-9 included
deliverables: <REPO>/selftest.py
status: delivered
attestation: edited only selftest.py
board_read: yes
hashes_judged: bs_pricing 12deadc4, synthetic 1414ff07, data_io 589f5c78, surface be111b3e, viz edc7196f, main 900228c8, requirements 60d0c169; selftest 34fbf338 (sha256 prefixes, identical before and after the mutation proof)
result: python selftest.py exit 0, 38/38 passed (bash-captured rc; the pipe-tail trap does not apply because output was redirected to a file). Clean chain status counts {0:124,1:134,2:6}, usable fraction 0.9773, 9 deep-OTM rows (price<1e-6) solved and inside the 1e-6 round trip. R12 n_checked 4389/4720 calendar and 4348/4680 butterfly (about 93%). Clean spline and rbf in-domain butterfly 0/4348 (R21 item 3 held).
report_only: noisy chain butterfly in-domain tick=0.01 rbf 1/3912 spline 8/3912; tick=0 rbf 0/3871 spline 0/3871 (tick rounding explains the noisy counts). Not asserted.
mutation_proof: run `py selftest.py --mutation-proof` (temp copies only; live hashes asserted unchanged, OK). RED as required: q_sign_in_d1, otm_boundary_to_put, term_structure_fixed_k_row, calendar_check_blind, butterfly_check_blind, calendar_mask_removed_scope, in_domain_old_union_rule, iv_returns_seed_value, viz_term_nan_mask_removed, viz_smile_nan_mask_removed, hover_drops_expiry, surface_z_in_decimals, loader_keeps_last_duplicate (retargeted to CSV loader `if key in seen`). Price-only acceptance alone is NOT caught: the vega>=1e-8 guard masks it (INFO row). Removing both (conv price-only AND usable = vega >= 0.0) goes RED: clean round trip max error 2.2e-01, verified manually in a scratch copy; the table row now carries that variant but the full table was not re-run after that final one-line edit.
lesson: A guard stacked behind another guard hides a mutation of the first; mutate the pair, or the proof reports a hole that is really defense in depth. Also a scoped diagnostic needs injections on both sides of the mask, and a presentation-layer NaN mask needs a noisy-chain fixture where the gap actually occurs.
friction: heredoc python edit scripts used for selftest.py edits (brief says Write/Edit); one tool call was interrupted by a user pause and resumed; first flow-board call needed forward slashes; no flow-board note posted.
