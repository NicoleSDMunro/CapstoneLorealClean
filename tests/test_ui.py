"""Teste do fluxo do Streamlit com triângulo sintético, sem dados empresariais."""
import runpy
from streamlit.testing.v1 import AppTest

samples=runpy.run_path("tests/test_smoke.py")
at=AppTest.from_file("app.py",default_timeout=50)
at.run()
assert not at.exception, [str(e) for e in at.exception]
assert len(at.tabs)==4, f"Esperadas quatro áreas; obtidas {len(at.tabs)}"
at.session_state["triangulo_file_bytes"]=samples["buf"].getvalue()
at.session_state["triangulo_file_name"]="triangulo_sintetico.xlsx"
at.run()
assert not at.exception, [str(e) for e in at.exception]
assert len(at.tabs)==4
print("UI PASS: quatro áreas, upload sintético, dados e cálculos")
