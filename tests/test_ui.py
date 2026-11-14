"""Teste de navegação das três áreas e processamento sem dados empresariais."""
import runpy
from streamlit.testing.v1 import AppTest

samples = runpy.run_path("tests/test_smoke.py")
at = AppTest.from_file("../app.py", default_timeout=120)

at.run()
assert not at.exception, [str(e) for e in at.exception]
assert len(at.radio) >= 1, "Navegação lateral ausente"

at.session_state["triangulo_file_bytes"] = samples["buf"].getvalue()
at.session_state["triangulo_file_name"] = "triangulo_sintetico.xlsx"
at.run()
assert not at.exception, [str(e) for e in at.exception]
assert any("Central de decisões" in str(t.value) for t in at.title)

at.radio[0].set_value("Análise do produto").run()
assert not at.exception, [str(e) for e in at.exception]
assert any("Decisão de abastecimento" in str(t.value) for t in at.title)

views = [radio for radio in at.radio if radio.label == "O que deseja avaliar?"]
assert len(views) == 1, "Subnavegação de produto não encontrada"
views[0].set_value("Riscos por mês").run()
assert not at.exception, [str(e) for e in at.exception]

at.radio[0].set_value("Resultados e confiabilidade").run()
assert not at.exception, [str(e) for e in at.exception]
assert any("Resultados e confiabilidade" in str(t.value) for t in at.title)

print("UI PASS: central, análise do produto, riscos e evidências históricas")
