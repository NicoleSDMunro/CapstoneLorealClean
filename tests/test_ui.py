"""Teste de navegação e processamento com Triângulo sintético."""
import runpy
from streamlit.testing.v1 import AppTest

samples=runpy.run_path("tests/test_smoke.py")
at=AppTest.from_file("../app.py",default_timeout=75)
at.run()
assert not at.exception, [str(e) for e in at.exception]
assert len(at.radio)>=1, "Navegação lateral ausente"
at.session_state["triangulo_file_bytes"]=samples["buf"].getvalue()
at.session_state["triangulo_file_name"]="triangulo_sintetico.xlsx"
at.run()
assert not at.exception, [str(e) for e in at.exception]
assert any("Central de Alertas" in str(t.value) for t in at.title)
at.session_state["nav_page"]="Riscos de estoque"
at.run()
assert not at.exception, [str(e) for e in at.exception]
assert any("Riscos de estoque" in str(t.value) for t in at.title)
print("UI PASS: navegação, leitura sintética e análise de riscos")
