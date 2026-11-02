project: Volitility-Model
role: handoff-documenter
task: HANDOFF lane - write README.md (run commands, IV rule R-1/R-2, limitations, open REVIEW-B items, case-study pointer)
deliverables: <REPO>/README.md
status: delivered
attestation: edited only README.md
board_read: yes
agent_memory: read, empty (no store existed); none written this run
flow_board_py: not run (no Bash); read KNOWLEDGE_BOARD.md from disk
verified_by_reading: main.py argparse and exit codes, selftest.py and oracle_check.py argv handling, data_io.py CSV rules and error text, surface.py report lines, CONTRACT sections 8/10/12, REVIEW_A R3/R14/R20, REVIEW_B sections 1-5, QA/ORACLE/BUILD-B/BUILD-C run-logs
hub_facts_cited_as_hub: tick=0 counts, live ticker smoke run numbers (ticker not named), BUILD-C 62/80 node count (from its run-log)
readme_hygiene: grep of README.md for non-ASCII, local paths, ticker symbol and <user>/<user> returned no matches
findings_for_hub: (1) main.py line 6 and selftest.py line 1184 contain a ticker symbol and will hit the R-10 ticker scan; owners BUILD-C and QA. (2) case-study/INDEX.md does not exist yet, so the README link dangles until the second commit. (3) RESOLVED by hub: oracle exit 0 on final bytes (oracle_check e44e67b8), README section 8 restated. (4) RESOLVED by hub: mutation proof after QA's last edit, exit 0, BASELINE rc=0 failed=[], 14 RED, 1 INFO; D12 stays open. (5) --ticker silently ignores --spot and --div (open). (6) RESOLVED by hub: ticker smoke run used default rbf.
operator_questions_remaining: which q branch produced q=0.0075 (OX-5)
update_note: edited in place in processed/ because rollup had already moved the inbox file; no second file created
lesson: A README written without Bash must quote literal output strings from the print statements, not from a reviewer's prose (REVIEW_B paraphrased the mutation-proof baseline line; the code string matched, but it had to be grepped to know). Also: a "clean" fixture mentioned in a verify step must be labelled as a test fixture when the CLI cannot produce it, or the operator cannot reproduce the number.
friction: skipped CONTRACT/REVIEW_A at first and read the needed sections only after the advisor pointed it out; no other re-lookups
