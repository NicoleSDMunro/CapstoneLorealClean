"""Teste do fluxo do Streamlit com triângulo sintético, sem dados empresariais."""
import runpy
from streamlit.testing.v1 import AppTest

samples=runpy.run_path("tests/test_smoke.py")
at=AppTest.from_file("../app.py",default_timeout=50)
at.run()
assert not at.exception, [str(e) for e in at.exception]
assert len(at.tabs)==5, f"Esperadas cinco áreas; obtidas {len(at.tabs)}"
at.session_state["triangulo_file_bytes"]=samples["buf"].getvalue()
at.session_state["triangulo_file_name"]="triangulo_sintetico.xlsx"
at.run()
assert not at.exception, [str(e) for e in at.exception]
assert len(at.tabs)==5
print("UI PASS: cinco áreas, upload sintético, dados e cálculos")
