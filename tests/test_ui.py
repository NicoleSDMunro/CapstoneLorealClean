"""UI: seleção explícita após a comparação de modelos, fluxo sem abas e tema único."""
import runpy
from streamlit.testing.v1 import AppTest

samples=runpy.run_path("tests/test_smoke.py")
at=AppTest.from_file("../app.py",default_timeout=120)
at.run()
assert not at.exception,[str(e) for e in at.exception]
assert not any(r.label=="Navegação" for r in at.radio)

at.session_state["triangulo_file_bytes"]=samples["buf"].getvalue()
at.session_state["triangulo_file_name"]="triangulo_sintetico.xlsx"
at.run()
assert not at.exception,[str(e) for e in at.exception]
assert any("Smart Launch" in str(x.value) for x in at.title)

def has_stage(text):
    return any(text in str(x.value) for x in at.markdown)

def selection(label):
    return next(x for x in at.selectbox if x.label==label)

assert has_stage("Dados e diagnóstico")
assert has_stage("Avaliação e seleção dos modelos")
assert not has_stage("Previsão mensal de demanda"),"Previsão antes do botão de confirmação"
assert not has_stage("Alternativas e decisão do planejador")
for label in ("FECHAMENTO · REVISÃO DO PLANO","HORIZONTE DOS GRÁFICOS",
              "ESCOLHER PRODUTO","ESCOLHER MODELO"):
    selection(label)

# Depois dos modelos, o usuário escolhe explicitamente um produto/modelo.
selection("ESCOLHER PRODUTO").set_value("P3").run()
assert not at.exception,[str(e) for e in at.exception]
selection("ESCOLHER MODELO").set_value("Naive").run()
assert not at.exception,[str(e) for e in at.exception]
assert not has_stage("Previsão mensal de demanda")
next(b for b in at.button if b.label=="Confirmar produto e modelo · analisar").click().run()
assert not at.exception,[str(e) for e in at.exception]
assert at.session_state["operational_P3"]=="Naive"
assert any(x["Produto"]=="P3" and x["Aprovado"]=="Naive"
           for x in at.session_state["approvals"])
assert has_stage("Previsão mensal de demanda")
for stage in ("Incerteza e evolução do estoque","Risco de excesso e prazo para agir",
              "Alternativas e decisão do planejador"):
    assert has_stage(stage),stage

# A troca de modelo invalida a análise até nova confirmação.
selection("ESCOLHER MODELO").set_value("Oficial").run()
assert not at.exception,[str(e) for e in at.exception]
assert not has_stage("Previsão mensal de demanda")
next(b for b in at.button if b.label=="Confirmar produto e modelo · analisar").click().run()
assert not at.exception,[str(e) for e in at.exception]
assert at.session_state["operational_P3"]=="Oficial"
assert has_stage("Previsão mensal de demanda")

# Os relatórios técnicos continuam opcionais, sem abas laterais.
detail=selection("EXPLORAR DETALHES")
for page in ("Previsão e modelos","Riscos de estoque","Impacto operacional",
             "Valor demonstrado","Histórico e metodologia"):
    selection("EXPLORAR DETALHES").set_value(page).run()
    assert not at.exception,(page,[str(e) for e in at.exception])
    assert has_stage("Dados e diagnóstico")
    assert has_stage("Previsão mensal de demanda")
selection("EXPLORAR DETALHES").set_value("Nenhuma análise aberta").run()
assert not at.exception,[str(e) for e in at.exception]

# A mudança do arquivo exige nova escolha; os seis produtos são reconhecidos.
at.session_state["triangulo_file_bytes"]=samples["buf_multi"].getvalue()
at.run()
assert not at.exception,[str(e) for e in at.exception]
assert "P6" in selection("ESCOLHER PRODUTO").options
assert not has_stage("Previsão mensal de demanda")
selection("ESCOLHER PRODUTO").set_value("P4").run()
assert not at.exception,[str(e) for e in at.exception]
selection("ESCOLHER MODELO").set_value("Oficial").run()
assert not at.exception,[str(e) for e in at.exception]
next(b for b in at.button if b.label=="Confirmar produto e modelo · analisar").click().run()
assert not at.exception,[str(e) for e in at.exception]
assert has_stage("Risco de excesso e prazo para agir")
print("UI PASS: tema unificado, fluxo guiado, seleção/approval e revisão de dados sem abas")
