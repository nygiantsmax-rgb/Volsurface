project: Volitility-Model
role: pipeline-builder
task: BUILD-C - viz.py, main.py, requirements.txt to CONTRACT 7/8 plus REVIEW_A R3 and R13
deliverables: <REPO>/viz.py, <REPO>/main.py, <REPO>/requirements.txt
status: delivered
lesson: plotly 7 fig.to_dict() base64-encodes numeric ndarrays ({dtype,bdata,shape}); read shapes from fig.data[i].z/.customdata. Also: a hand-built fake Surface in a module self-test goes stale when the real dataclass gains fields the real helpers read (viz selftest broke on k_lo); keep fixtures in step or build from the real modules.
domain: Volitility-Model
decision: R3 implemented in main.py (params line always, exact ticker note on --ticker, ticker path not run - needs network). R13 implemented in viz.py (in_domain False -> y NaN, from term_structure output, not recomputed). R14 DEFERRED per flow-lead: hovertemplate and customdata shape unchanged, so the 3D surface corners are unlabelled as extrapolated; open exception for REVIEW-B.
verification: main.py --no-open under python -W error against real modules exit 0 (Git Bash $?, no PowerShell tool); NaN count per Term trace equals count of in_domain False (K=50:60, K=80:6, K=100:0, K=120:6, K=150:60, rbf and spline); no STUB markers remain.
friction: no SendMessage and no PowerShell tool in this spoke; viz selftest fixture needed k_lo/k_hi/in_domain after BUILD-B landed; REVIEW_A did not exist during first build; first flow-board call with backslash path failed
