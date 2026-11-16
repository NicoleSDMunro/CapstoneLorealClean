"""Teste do Smart Launch em página única e seleção supervisionada de modelos."""
import runpy
from streamlit.testing.v1 import AppTest

samples = runpy.run_path("tests/test_smoke.py")
at = AppTest.from_file("../app.py", default_timeout=120)

at.run()
assert not at.exception, [str(e) for e in at.exception]
assert not any(r.label == "Navegação" for r in at.radio), "Não deve existir menu lateral de abas"

at.session_state["triangulo_file_bytes"] = samples["buf"].getvalue()
at.session_state["triangulo_file_name"] = "triangulo_sintetico.xlsx"
at.run()
assert not at.exception, [str(e) for e in at.exception]
assert any("Central de decisões" in str(t.value) for t in at.title)

for label_name in ("PRODUTO", "FECHAMENTO · REVISÃO DO PLANO",
                   "HORIZONTE", "VISÃO", "EXPLORAR DETALHES"):
    assert any(item.label == label_name for item in at.selectbox), label_name
assert any("Avaliação e seleção dos modelos" in str(x.value) for x in at.markdown), (
    "Resumo dos modelos deve ficar antes dos indicadores"
)
assert not any(r.label in ("Navegação", "O que deseja avaliar?", "O que deseja consultar?")
               for r in at.radio)

# A Central trabalha com qualquer quantidade de produtos e expõe o ranking por SKU.
at.session_state["triangulo_file_bytes"] = samples["buf_multi"].getvalue()
at.run()
assert not at.exception, [str(e) for e in at.exception]
product_filter = next(x for x in at.selectbox if x.label == "PRODUTO")
assert "P6" in product_filter.options, product_filter.options
product_filter.set_value("P4").run()
assert not at.exception, [str(e) for e in at.exception]
mode_filter = next(x for x in at.selectbox if x.label == "VISÃO")
mode_filter.set_value("Analista").run()
assert not at.exception, [str(e) for e in at.exception]

# No lugar de abas, o detalhamento é acessível na mesma página.
detail_select = next(x for x in at.selectbox if x.label == "EXPLORAR DETALHES")
for target in ("Riscos de estoque", "Previsão e modelos", "Impacto operacional",
               "Valor demonstrado", "Histórico e metodologia"):
    detail_select = next(x for x in at.selectbox if x.label == "EXPLORAR DETALHES")
    detail_select.set_value(target).run()
    assert not at.exception, (target, [str(e) for e in at.exception])
    assert any("Central de decisões" in str(t.value) for t in at.title)

# Retorna ao início sem esconder a central nem recriar navegação lateral.
next(x for x in at.selectbox if x.label == "EXPLORAR DETALHES").set_value(
    "Nenhuma análise aberta"
).run()
assert not at.exception, [str(e) for e in at.exception]
assert not any(r.label == "Navegação" for r in at.radio)
print("UI PASS: painel único, resumo MAPE, seis SKUs e detalhes sem abas")
