project: Volitility-Model
role: pipeline-builder
task: BUILD-C - viz.py, main.py, requirements.txt to CONTRACT.md sections 7 and 8
deliverables: <REPO>/viz.py, <REPO>/main.py, <REPO>/requirements.txt
status: delivered
lesson: plotly 7 fig.to_dict() base64-encodes numeric ndarrays ({dtype,bdata,shape}), so any gate that reads shape or values from to_dict() sees a dict; read fig.data[i].z/.customdata instead (strings like hovertemplate/name/title stay plain). Also: an object-dtype customdata (numbers plus a date label) survives as an ndarray.
domain: Volitility-Model
friction: no SendMessage tool in this spoke so the QA-relevant plotly base64 notice went to the flow board and final report instead; flow-board.py first call from a bash path with backslashes failed (mangled path), fixed by forward slashes; REVIEW_A.md did not exist during the build so no ruling was applied (nothing relayed by hub); no stubs left in final source (BUILD-A/B real modules landed before the end; viz stubs removed)
