project: Volitility-Model
role: pipeline-builder
task: BUILD-C fix round R-9 (D1, D5, D7, OX-2) on top of CONTRACT 7/8 + REVIEW_A R3, R13
deliverables: <REPO>/viz.py, <REPO>/main.py, <REPO>/requirements.txt
status: delivered
attestation: edited only viz.py, main.py and requirements.txt
board_read: yes
decision: R3 implemented (params line first, then notes, then the exact ticker note; ticker path not run, needs network). R13 implemented (term-structure in_domain False -> y NaN). OX-2 implemented in viz.py (smile line y NaN where Surface.in_domain row nearest the maturity is False; proved on default noisy chain T=1/12: NaN idx == in_domain False idx, 62 of 80 nodes, rbf and spline). R14 DEFERRED per flow-lead (final): hovertemplate and customdata unchanged, so the 3D surface corners are unlabelled as extrapolated; open exception.
fixes: D1 control total 1 now compares a raw file line count against loader kept+rejected for --csv (can fail); --ticker and synthetic print "rejected: n/a" instead of a number. D5 docstrings and hover text now say out-of-domain renders as a gap (x markers and the in-range hover field removed). D7 noise/seed note now printed after the params line.
verification: python -W error main.py --no-open exit 0 for default rbf and for spline + strike axis (Git Bash $?; no PowerShell tool in this spoke); viz.py selftest exit 0; csv path with a bad row reports 3 file rows = 2 kept + 1 rejected; hashes viz.py edc7196f05e157d7..., main.py 900228c83be98e19...
lesson: A control total that sums the loader's own two outputs and asserts they equal the sum cannot fail; anchor it to a count taken from the raw source by a separate path, and where no independent count exists print n/a rather than a number that cannot be wrong. Also a hover/docstring describing a marker style must be re-checked when a NaN gap replaces the marker.
friction: no SendMessage and no PowerShell tool in this spoke, so hub notice is in the final report and exit codes are from Git Bash
