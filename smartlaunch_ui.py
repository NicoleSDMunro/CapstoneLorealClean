"""Smart Launch — central de alertas mensal, sem números ilustrativos."""
import hashlib
import html
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from smartlaunch_core import (
    MODEL, SHEETS, LIM, N, label, load_data, known, forecast,
    simulate, impacts, fmt,
)
from smartlaunch_monthly import evaluate_models
from smartlaunch_validation import (
    reconstruct_history, first_alerts, latest_verifiable_close,
    available_origin_reviews, EVENT_YES, EVENT_NO,
)

st.set_page_config(page_title="Smart Launch | Central de Alertas", page_icon="📦", layout="wide")
st.markdown("""
<style>
:root {color-scheme:light;}
.stApp {background:#f8f8f7; color:#141414;}
[data-testid="stSidebar"] {background:#ffffff; border-right:1px solid #e4e4e1;}
[data-testid="stHeader"] {background:#f8f8f7;}
[data-testid="stMetric"] {background:#ffffff; border:1px solid #e4e4e1; border-radius:16px; padding:16px;}
[data-testid="stMetricLabel"] {color:#6f6f6f;}
h1,h2,h3 {letter-spacing:-.035em; color:#111!important;}
h1 {font-weight:750!important;}
div[data-testid="stVerticalBlockBorderWrapper"]>div {border-color:#e3e4e1!important; border-radius:17px!important;}
.stButton>button {border-radius:30px; border:1px solid #171717; min-height:42px;}
.stButton>button[kind="primary"] {background:#111; color:white;}
div[data-testid="stAlert"] {border-radius:12px;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {padding:3px 0;}
.cardeyebrow {font-size:12px; font-weight:650; letter-spacing:.07em; color:#888; text-transform:uppercase;}
.note {font-size:13px; color:#777;}
.pill {display:inline-block; margin:2px 6px 2px 0; padding:5px 10px; border-radius:20px; font-size:12px; font-weight:650; background:#f1f1ef;}
.pill-red {color:#af2517; background:#fff0ed;}
.pill-amber {color:#895b00; background:#fff3d9;}
.pill-green {color:#165e3c; background:#e9f5eb;}
.pill-muted {color:#595959; background:#eeeeec;}
.timeline {display:grid;gap:0;overflow-x:auto;min-width:640px;}
.timeline-cell {padding:11px 2px;text-align:center;border-bottom:1px solid #ebebe8;font-size:13px;min-height:46px;}
.timeline-head {font-size:12px;color:#777;font-weight:650;}
.timeline-product {text-align:left;font-weight:700;padding-left:8px;}
.tdot {display:inline-block;width:26px;height:26px;line-height:26px;border-radius:50%;color:white;font-size:11px;font-weight:750;text-align:center;margin:1px;}
.tdot-e {background:#b42318;}
.tdot-r {background:#e5ac38;color:#382700;}
.tdot-p {background:#171717;}
</style>
""", unsafe_allow_html=True)

NAV = [
    "Visão geral", "Atualização mensal", "Previsão e modelos",
    "Riscos de estoque", "Simulador de decisões",
    "Validação histórica dos alertas", "Histórico e metodologia",
]
DEFAULT_METHOD = "Normal (0, s)"
LIMIT_ALERT = 0.025


def navigate(page, product=None):
    st.session_state["nav_page"] = page
    if product is not None:
        st.session_state["selected_product"] = product


def approve_model(product, new_model, close):
    old = st.session_state.get("operational_" + product, MODEL[product])
    st.session_state["operational_" + product] = new_model
    st.session_state.setdefault("approvals", []).append({
        "Produto": product, "Fechamento": label(close),
        "Anterior": old, "Aprovado": new_model,
        "Registrado em (UTC)": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })


def update_uploaded_file(uploaded):
    if uploaded is None:
        return
    data = uploaded.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    if digest != st.session_state.get("data_digest"):
        st.session_state["triangulo_file_bytes"] = data
        st.session_state["triangulo_file_name"] = uploaded.name
        st.session_state["data_digest"] = digest
        st.session_state["uploaded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        st.session_state.pop("selected_revision", None)
        for key in ("validation_asof","validation_product","validation_model","validation_origins","validation_horizon"):
            st.session_state.pop(key, None)


def explain_empty():
    st.info("Carregue o Triângulo atualizado para gerar previsões, comparar modelos e mostrar alertas reais. Nenhum valor demonstrativo será exibido.")
    if st.button("Ir para atualização mensal", type="primary", on_click=navigate, args=("Atualização mensal",)):
        pass


def preview_forecast(product, close, blocks, operational_model):
    """Previsão pontual histórica sem estimar probabilidades quando faltam resíduos."""
    data = blocks[SHEETS[product]]
    revision = close + 1
    if revision not in data["PV"].index:
        return None, "Revisão " + label(revision) + " não encontrada para PV."
    months = [m for m in sorted(data["PV"].columns)
              if m > close and m in data["PROD"].columns]
    if not months:
        return None, "Não existem meses futuros nas colunas do Triângulo."
    try:
        values = forecast(product, months, close, blocks, model=operational_model)
        if len(values) != len(months) or not np.isfinite(values).all():
            return None, "A previsão central contém valores ausentes."
        return pd.DataFrame({"Mês": [label(m) for m in months],
                             "Previsão central (un.)": np.round(values).astype(int)}), None
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        return None, str(exc)


def show_available_forecast(product, close, blocks):
    frame, issue = preview_forecast(product, close, blocks,
                                    st.session_state["operational_" + product])
    if frame is None:
        st.caption("Previsão central indisponível para " + product + ": " + issue)
    else:
        st.caption("Previsão pontual do modelo " +
                   st.session_state["operational_" + product] +
                   ". Não implica probabilidade de excesso ou ruptura.")
        st.dataframe(frame, hide_index=True, use_container_width=True)
    return frame is not None


def rows_from_sim(res):
    ex = (res["cov"] >= LIM).mean(axis=0)
    ru = (res["lost"] > 0).mean(axis=0)
    stock = np.percentile(res["stock"], 50, axis=0)
    cover = np.percentile(res["cov"], 50, axis=0)
    rows = []
    for j, month in enumerate(res["months"]):
        window = bool(res["active"][j])
        deadline = month - res["ltm"]
        rows.append({
            "Período": month,
            "Mês": label(month),
            "Excesso (%)": round(float(ex[j])*100, 1),
            "Ruptura (%)": round(float(ru[j])*100, 1),
            "Cobertura P50 (dias)": round(float(cover[j])),
            "Estoque P50 (un.)": round(float(stock[j])),
            "Previsão (un.)": round(float(res["center"][j])),
            "Janela crítica": window,
            "Alerta excesso": window and ex[j] > LIMIT_ALERT,
            "Alerta ruptura": window and ru[j] > LIMIT_ALERT,
            "Prazo do lote": label(deadline),
        })
    return pd.DataFrame(rows)


def eligible_lots(res, close):
    lots = []
    for j, month in enumerate(res["months"]):
        volume = float(res["production"][j])
        if volume <= 0:
            continue
        deadline = month - res["ltm"]
        lots.append({
            "índice": j, "mês": month, "volume": volume,
            "prazo": deadline, "alterável": deadline > close,
        })
    return lots


def classify_action(res, close, risk_month, risk_type):
    doable = any(lot["alterável"] and lot["mês"] <= risk_month for lot in eligible_lots(res, close))
    if doable:
        return "Avaliar fornecedor", "Existe lote futuro ainda dentro do prazo teórico para alteração."
    if risk_type == "excesso":
        return "Avaliação comercial", "Não há lote alterável a tempo para mitigar o risco identificado."
    return "Monitorar e avaliar alocação", "Não há lote alterável que chegue antes do mês de risco."


def risk_plot(res, rowset, column, color):
    vals = rowset[column].to_numpy(float)
    active = rowset["Janela crítica"].to_numpy(bool)
    is_alert = vals > 100*LIMIT_ALERT
    colors = [color if active[i] and is_alert[i] else "#d8d8d6" for i in range(len(vals))]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=rowset["Mês"], y=vals, marker_color=colors, text=[f"{x:.1f}" for x in vals],
        textposition="outside", hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=100*LIMIT_ALERT, line_width=1, line_dash="dash", line_color="#444",
                  annotation_text="Gatilho 2,5%", annotation_position="top left")
    ymax = max(10, float(vals.max())*1.25) if len(vals) else 10
    fig.update_layout(
        template="plotly_white", height=315, margin=dict(l=8,r=12,t=25,b=10),
        paper_bgcolor="white", plot_bgcolor="white", yaxis=dict(title="Probabilidade (%)",range=[0,ymax]),
        xaxis=dict(title=None), showlegend=False, font=dict(color="#222"),
    )
    return fig


def timeline_markup(panels, close):
    months = [close+i for i in range(1, 8)]
    cols = len(months)+1
    elements = ['<div class="timeline" style="grid-template-columns:100px repeat(7,minmax(72px,1fr))">']
    elements.append('<div class="timeline-cell timeline-head timeline-product">Produto</div>')
    for month in months:
        elements.append('<div class="timeline-cell timeline-head">' + label(month) + '</div>')
    for product in MODEL:
        elements.append('<div class="timeline-cell timeline-product">' + product + '</div>')
        res = panels.get(product)
        if res is None:
            elements.extend(['<div class="timeline-cell">—</div>'] * len(months))
            continue
        by_month = {row["Período"]:row for _,row in rows_from_sim(res).iterrows()}
        lots = eligible_lots(res, close)
        for month in months:
            dots=[]
            item = by_month.get(month)
            if item is not None and item["Alerta excesso"]:
                dots.append('<span class="tdot tdot-e" title="Excesso">E</span>')
            if item is not None and item["Alerta ruptura"]:
                dots.append('<span class="tdot tdot-r" title="Ruptura">R</span>')
            if any(lot["prazo"] == month and lot["alterável"] for lot in lots):
                dots.append('<span class="tdot tdot-p" title="Prazo de lote">P</span>')
            elements.append('<div class="timeline-cell">' + (''.join(dots) or '·') + '</div>')
    elements.append('</div>')
    return ''.join(elements)


def scenario_plan(res, index, action):
    plan = res["production"].copy()
    volume = plan[index]
    if action == "Reduzir 25%":
        plan[index] = volume*.75
    elif action == "Reduzir 50%":
        plan[index] = volume*.5
    elif action == "Cancelar lote":
        plan[index] = 0
    elif action == "Aumentar 25%":
        plan[index] = volume*1.25
    elif action == "Adiar 1 mês":
        if index + 1 >= len(plan):
            return None
        plan[index] = 0
        plan[index+1] += volume
    elif action == "Antecipar 1 mês":
        if index - 1 < 0:
            return None
        plan[index] = 0
        plan[index-1] += volume
    return plan


with st.sidebar:
    st.markdown("## Smart Launch")
    st.caption("Apoio à decisão em lançamentos")
    st.divider()
    page = st.radio("Navegação", NAV, key="nav_page", label_visibility="collapsed")
    st.divider()
    uploaded_sidebar = st.file_uploader("Atualizar Triângulo", type=["xlsx"], key="sidebar_upload")
    update_uploaded_file(uploaded_sidebar)
    st.caption("Os dados ficam na sessão Streamlit. Não use hospedagem pública sem controle de acesso.")

if page == "Atualização mensal":
    st.title("Atualização mensal")
    st.write("Carregue a nova versão do Triângulo. O processamento utiliza os dados disponíveis em cada fechamento.")
    uploaded_main = st.file_uploader("Arquivo Triângulo (.xlsx)", type=["xlsx"], key="main_upload")
    update_uploaded_file(uploaded_main)

file = st.session_state.get("triangulo_file_bytes")
if file is None:
    if page != "Atualização mensal":
        st.title("Central de Alertas" if page=="Visão geral" else page)
    explain_empty()
    st.stop()

try:
    base, blocks = load_data(file)
except Exception as exc:
    st.error("Não foi possível validar o arquivo: " + str(exc))
    st.caption("Esperado: Base, PRODUTO 1–3 e respectivas abas BENCH do Triângulo V2.")
    st.stop()

if "data_digest" not in st.session_state:
    st.session_state["data_digest"] = hashlib.sha256(file).hexdigest()
for product in MODEL:
    st.session_state.setdefault("operational_"+product, MODEL[product])

revisions = None
for product, sheet in SHEETS.items():
    data = blocks[sheet]
    revs = set(data["PV"].index)&set(data["PROD"].index)&set(data["EST"].index)
    valid = {rev for rev in revs if rev-1 in data["EST"].columns}
    revisions = valid if revisions is None else revisions & valid
revisions = sorted(revisions or [])
if not revisions:
    st.error("Nenhuma revisão comum entre PV, produção e estoque para os três produtos. Confira a auditoria da base; não foram gerados alertas.")
    st.stop()

with st.sidebar:
    st.selectbox("Revisão do plano", revisions, index=len(revisions)-1,
                 format_func=label, key="selected_revision")
    st.selectbox("Produto analisado", list(MODEL), key="selected_product")
review = st.session_state["selected_revision"]
close = review - 1
chosen = st.session_state["selected_product"]
method = st.session_state.get("simulation_method", DEFAULT_METHOD)
persistent = bool(st.session_state.get("simulation_persistent",False))

results = {}
errors = {}
rankings = {}
for product in MODEL:
    try:
        _detail, _rank, _winner = evaluate_models(product, close, blocks, forecast, known)
        rankings[product] = (_detail, _rank, _winner)
    except Exception as exc:
        rankings[product] = (pd.DataFrame(), pd.DataFrame(), None)
        errors["rank_"+product] = str(exc)
    try:
        results[product] = simulate(product, close, blocks, base, method, persistent,
                                    operational_model=st.session_state["operational_"+product])
    except Exception as exc:
        results[product] = None
        errors[product] = str(exc)

ready_count = sum(x is not None for x in results.values())
status = "Processamento completo" if ready_count==len(MODEL) else "Processamento parcial"
file_name = st.session_state.get("triangulo_file_name","Triângulo carregado na sessão")
st.caption("Fechamento: " + label(close) + "   ·   Revisão: " + label(review) +
           "   ·   " + status + "   ·   Arquivo: " + file_name)
if ready_count < len(MODEL):
    st.warning("Probabilidades não calculadas para " +
               ", ".join(p for p in MODEL if results[p] is None) +
               ". Sem simulação válida NÃO significa risco zero.")
    with st.expander("Entender por que a simulação está indisponível"):
        st.caption("O Smart Launch usa a venda do mês m na revisão m+1. "
                   "Se o último registro é mar/26, a última venda confirmada pelo "
                   "método pode ser fev/26. Para avaliar o fechamento de mar/26, "
                   "é necessária a revisão abr/26.")
        for product in MODEL:
            if results[product] is None:
                st.write("**" + product + ":** " + errors.get(product, "Sem dados suficientes"))
        st.caption("Mesmo com uma previsão central disponível, a simulação "
                   "precisa de pelo menos dois erros históricos elegíveis do arranque. "
                   "Não preenchemos probabilidades com valores fictícios.")

if page == "Visão geral":
    st.title("Central de Alertas")
    st.write("O que merece atenção neste fechamento — e se ainda dá tempo de agir.")
    st.caption("Os números abaixo são calculados a partir do Excel enviado, não de uma base demonstrativa.")
    counts = {"ex":0,"ru":0,"open":0}
    priorities=[]
    for product,res in results.items():
        if res is None:
            continue
        frame=rows_from_sim(res)
        counts["ex"]+=bool(frame["Alerta excesso"].any())
        counts["ru"]+=bool(frame["Alerta ruptura"].any())
        counts["open"]+=sum(lot["alterável"] for lot in eligible_lots(res,close))
        threats=frame[frame["Alerta excesso"]|frame["Alerta ruptura"]]
        if not threats.empty:
            row=threats.iloc[0]
            typ = "excesso" if row["Alerta excesso"] else "ruptura"
            prob = row["Excesso (%)"] if typ=="excesso" else row["Ruptura (%)"]
            act,desc=classify_action(res,close,row["Período"],typ)
            priorities.append((0,row["Período"],product,typ,prob,row,act,desc))
        else:
            priorities.append((1,pd.Period("2099-01","M"),product,None,0,None,"Monitoramento","Sem gatilho na janela crítica."))
    mc=st.columns(5)
    for col,title,value in zip(mc,
        ["Produtos monitorados","Risco de excesso","Risco de ruptura","Lotes com prazo aberto","Sem simulação válida"],
        [len(MODEL),
         f'{counts["ex"]}/{ready_count}' if ready_count else "—",
         f'{counts["ru"]}/{ready_count}' if ready_count else "—",
         counts["open"] if ready_count else "—",
         len(MODEL)-ready_count]):
        col.metric(title,value)
    if ready_count<len(MODEL):
        st.caption("Excesso e ruptura: ocorrências apenas entre os produtos com "
                   "simulação válida (numerador / avaliados). O traço indica "
                   "não calculado, não ausência de risco.")
    st.subheader("Prioridades do fechamento")
    for _,_,product,typ,prob,row,act,description in sorted(priorities):
        res=results[product]
        with st.container(border=True):
            lead,metrics,go_button=st.columns([2.1,2.2,.8],vertical_alignment="center")
            with lead:
                st.markdown("### Produto " + product)
                if typ:
                    word="Excesso de estoque" if typ=="excesso" else "Ruptura"
                    color="pill-red" if typ=="excesso" else "pill-amber"
                    st.markdown('<span class="pill '+color+'">Risco: '+word+
                                '</span><span class="pill pill-muted">Ação: '+html.escape(act)+'</span>',
                                unsafe_allow_html=True)
                    st.caption(description)
                    active_deadlines=[lot["prazo"] for lot in eligible_lots(res,close)
                                      if lot["alterável"] and lot["mês"]<=row["Período"]]
                    if active_deadlines:
                        st.caption("Próximo prazo de decisão: "+label(min(active_deadlines))+
                                   " (mês teórico; confirmar com fornecedor).")
                    else:
                        st.caption("Prazo de intervenção no fornecedor: indisponível para este risco.")
                else:
                    st.markdown('<span class="pill pill-green">Sem gatilho no período</span>',unsafe_allow_html=True)
                    st.caption("O acompanhamento continua mensalmente.")
            with metrics:
                if typ:
                    m1,m2,m3=st.columns(3)
                    m1.metric("Probabilidade",f"{prob:.1f}%")
                    m2.metric("Mês de risco",row["Mês"])
                    m3.metric("Cobertura P50",f'{int(row["Cobertura P50 (dias)"])} dias')
                st.caption("Modelo em uso: " + st.session_state["operational_"+product] +
                           "   ·   Melhor testado: " + (rankings[product][2] or "Não elegível"))
            with go_button:
                st.button("Analisar produto",key="open_"+product, type="primary",
                          on_click=navigate,args=("Riscos de estoque",product))
    missing=[p for p in MODEL if results[p] is None]
    if missing:
        st.info("Sem avaliação probabilística: " + ", ".join(missing) +
                ". Previsões centrais eventualmente disponíveis aparecem abaixo.")
        st.subheader("Previsões disponíveis sem simulação de risco")
        for product in missing:
            with st.expander("Produto " + product + " — " + errors.get(product, "Sem simulação")):
                show_available_forecast(product, close, blocks)
    st.subheader("Linha do tempo dos alertas")
    st.caption("E = excesso · R = ruptura · P = prazo ainda aberto de lote. São exibidos apenas alertas dentro da janela crítica.")
    with st.container(border=True):
        st.markdown(timeline_markup(results,close),unsafe_allow_html=True)

elif page == "Atualização mensal":
    st.subheader("Auditoria da base enviada")
    st.success("Estrutura básica do Triângulo reconhecida: " + file_name)
    checks=[]
    for product,sheet in SHEETS.items():
        b=blocks[sheet]
        counts={k:len(b[k].index) if k in b else 0 for k in ("PV","PROD","EST")}
        checks.append({"Produto":product,"PV (revisões)":counts["PV"],
                       "Produção (revisões)":counts["PROD"],
                       "Estoque (revisões)":counts["EST"],
                       "Simulação": "Disponível" if results[product] is not None else "Indisponível",
                       "Motivo":errors.get(product,"")})
    st.dataframe(pd.DataFrame(checks),hide_index=True,use_container_width=True)
    c1,c2,c3=st.columns(3)
    c1.metric("Fechamento selecionado",label(close))
    c2.metric("Revisão utilizada",label(review))
    c3.metric("Produtos com simulação",f"{ready_count}/{len(MODEL)}")
    st.info("O Excel deve conter as revisões anteriores. Este protótipo não salva arquivos nem decisões de maneira permanente.")
    st.caption("Como o Triângulo funciona: o realizado de mar/26 é recuperado "
               "na revisão abr/26. Para simular um fechamento histórico, mantenha "
               "todas as revisões originais e escolha a revisão correspondente "
               "no menu lateral, sem apagar as linhas posteriores.")
    with st.expander("Vendas conhecidas por produto"):
        for product,sheet in SHEETS.items():
            observed=known(blocks[sheet]["PV"],close)
            st.markdown("**"+product+"**")
            if observed.empty:
                st.caption("Sem vendas realizadas neste fechamento.")
            else:
                st.dataframe(pd.DataFrame({"Mês":[label(x) for x in observed.index],
                                           "Vendido (un.)":observed.values}),hide_index=True)
    st.caption("Identificador do arquivo (SHA-256): " + st.session_state["data_digest"][:16] +
               "… · O arquivo é processado no servidor da sessão, que deve ter acesso protegido.")

elif page == "Previsão e modelos":
    st.title("Previsão e modelos")
    st.write("Reavaliar mensalmente o erro histórico sem alterar silenciosamente a previsão operacional.")
    product=chosen
    detail,ranking,winner=rankings[product]
    operational=st.session_state["operational_"+product]
    m1,m2,m3=st.columns(3)
    m1.metric("Produto analisado",product)
    m2.metric("Modelo em uso",operational)
    m3.metric("Melhor no backtest atual",winner or "Não elegível")
    st.caption("Comparação experimental: MEA-P, MEA, Oficial e Naive nos mesmos pares origem/alvo, h1–h3.")
    if ranking.empty:
        st.warning("Não há pares comparáveis suficientes para determinar um vencedor neste fechamento.")
    else:
        st.dataframe(ranking,hide_index=True,use_container_width=True)
        st.warning("A elegibilidade deste ranking reduzido ainda precisa ser homologada contra os 49 modelos e o protocolo final do notebook do TCC.")
        if winner and winner!=operational:
            st.info("Novo vencedor observado: " + winner +
                    ". O modelo operacional permanece " + operational + " até aprovação.")
            st.button("Aprovar mudança para "+winner, type="primary",
                      on_click=approve_model,args=(product,winner,close))
        else:
            st.success("Nenhuma troca operacional sugerida neste fechamento.")
        if operational != MODEL[product]:
            st.button("Restaurar modelo inicial do TCC",on_click=approve_model,
                      args=(product,MODEL[product],close))
    res=results[product]
    if res is not None:
        chart=go.Figure()
        if len(res["months"]):
            chart.add_trace(go.Scatter(x=[label(m) for m in res["months"]],
                y=res["center"],mode="lines+markers",
                name="Previsão operacional",line=dict(color="#111",width=3)))
            pv=blocks[SHEETS[product]]["PV"]
            try:
                official=forecast(product,res["months"],close,blocks,model="Oficial")
                chart.add_trace(go.Scatter(x=[label(m) for m in res["months"]],
                    y=official,mode="lines+markers",name="Plano Oficial",
                    line=dict(color="#c73b22",dash="dash")))
            except Exception:
                pass
        chart.update_layout(template="plotly_white",height=335,
                            xaxis_title="Mês projetado",yaxis_title="Unidades",
                            margin=dict(l=10,r=10,t=12,b=10))
        st.plotly_chart(chart,use_container_width=True)
        st.caption("O gráfico usa a previsão recalculada no fechamento selecionado.")
    if not detail.empty:
        with st.expander("Inspecionar cada erro de validação"):
            st.dataframe(detail,hide_index=True,use_container_width=True)

elif page == "Riscos de estoque":
    st.title("Riscos de estoque")
    product=chosen
    res=results[product]
    if res is None:
        st.warning("Não há simulação probabilística válida para " + product + ": " +
                   errors.get(product, "Sem informação suficiente"))
        st.info("Uma previsão central pode existir mesmo quando o histórico de "
                "erros ainda não permite calcular probabilidades.")
        show_available_forecast(product, close, blocks)
        st.stop()
    frame=rows_from_sim(res)
    st.write("Produto "+product+" · modelo "+st.session_state["operational_"+product]+
             " · "+str(N)+" cenários · "+str(res["window"])+" meses na janela crítica")
    c1,c2,c3=st.columns(3)
    c1.metric("Estoque inicial",fmt(res["e0"])+" un.")
    c2.metric("Desvio-padrão dos erros",fmt(res["sd"])+" un.")
    c3.metric("Erros usados",len(res["errors"]))
    ex_col,ru_col=st.columns(2)
    with ex_col:
        with st.container(border=True):
            st.markdown("#### Chance de estoque acima de seis meses")
            st.caption("Cobertura ≥ 180 dias · linha tracejada indica limiar de alerta de 2,5%.")
            st.plotly_chart(risk_plot(res,frame,"Excesso (%)","#b42318"),use_container_width=True)
    with ru_col:
        with st.container(border=True):
            st.markdown("#### Chance de venda perdida (ruptura)")
            st.caption("Venda não atendida · linha tracejada indica limiar de alerta de 2,5%.")
            st.plotly_chart(risk_plot(res,frame,"Ruptura (%)","#d39b24"),use_container_width=True)
    st.subheader("Riscos e encaminhamentos por mês")
    display=frame[["Mês","Previsão (un.)","Estoque P50 (un.)",
                   "Cobertura P50 (dias)","Excesso (%)","Ruptura (%)",
                   "Janela crítica","Alerta excesso","Alerta ruptura"]]
    st.dataframe(display,hide_index=True,use_container_width=True)
    flagged=frame[frame["Alerta excesso"]|frame["Alerta ruptura"]]
    if flagged.empty:
        st.info("Sem alertas disparados dentro da janela crítica neste fechamento.")
    else:
        for _,row in flagged.iterrows():
            typ="excesso" if row["Alerta excesso"] else "ruptura"
            act,reason=classify_action(res,close,row["Período"],typ)
            st.markdown("**"+row["Mês"]+" · "+typ.capitalize()+"** — "+act+". "+reason)
    st.subheader("Evolução do risco entre fechamentos")
    st.caption("Acompanha a probabilidade estimada para o mesmo mês-alvo conforme novas revisões ficam disponíveis.")
    target=st.selectbox("Mês-alvo",list(res["months"]),format_func=label,key="risk_target")
    past=[]
    for old_review in revisions[-9:]:
        prev_close=old_review-1
        if prev_close>close or target<=prev_close:
            continue
        try:
            past_sim=simulate(product,prev_close,blocks,base,method,persistent,
                              operational_model=st.session_state["operational_"+product])
            if target in past_sim["months"]:
                j=past_sim["months"].index(target)
                if bool(past_sim["active"][j]):
                    past.append({"Fechamento":label(prev_close),
                                 "Excesso (%)":100*float((past_sim["cov"][:,j]>=LIM).mean()),
                                 "Ruptura (%)":100*float((past_sim["lost"][:,j]>0).mean())})
        except (ValueError,KeyError,IndexError):
            pass
    if len(past)>=2:
        pframe=pd.DataFrame(past)
        line=go.Figure()
        for column,color in (("Excesso (%)","#b42318"),("Ruptura (%)","#d39b24")):
            line.add_trace(go.Scatter(x=pframe["Fechamento"],y=pframe[column],
                                      mode="lines+markers",name=column,
                                      line=dict(color=color,width=3)))
        line.update_layout(template="plotly_white",height=280,margin=dict(l=8,r=8,t=15,b=10),
                           yaxis_title="Probabilidade (%)")
        st.plotly_chart(line,use_container_width=True)
    else:
        st.info("Ainda não há fechamentos históricos suficientes com simulação válida para mostrar a evolução deste mês-alvo.")

elif page == "Simulador de decisões":
    st.title("Simulador de decisões")
    product=chosen
    res=results[product]
    if res is None:
        st.warning("A simulação não está disponível: "+errors.get(product,"Dados insuficientes"))
        st.stop()
    st.caption("Produto "+product+" · Fechamento "+label(close)+
               " · lead time arredondado: "+str(res["ltm"])+" meses.")
    lots=eligible_lots(res,close)
    if lots:
        st.subheader("Lotes e prazos operacionais")
        lotstable=pd.DataFrame([{
            "Mês do lote":label(lot["mês"]),
            "Quantidade (un.)":round(lot["volume"]),
            "Prazo teórico":label(lot["prazo"]),
            "Situação":"Alterável pelo LT" if lot["alterável"] else "Prazo vencido",
        } for lot in lots])
        st.dataframe(lotstable,hide_index=True,use_container_width=True)
    else:
        st.info("Nenhum lote de produção futura identificado.")
    open_lots=[lot for lot in lots if lot["alterável"]]
    if not open_lots:
        st.error("Não existem lotes alteráveis pelo prazo de fornecimento neste fechamento.")
        st.info("Ação junto ao fornecedor indisponível. Avaliar encaminhamento comercial ou monitoramento.")
        st.caption("Não exibimos cortes de lote como executáveis após o vencimento do prazo.")
    else:
        st.success(str(len(open_lots))+" lote(s) ainda dentro do prazo teórico. A possibilidade contratual depende da L'Oréal.")
        names={lot["índice"]: label(lot["mês"])+" · "+fmt(lot["volume"])+" un. · prazo "+label(lot["prazo"])
               for lot in open_lots}
        selected=st.selectbox("Lote para análise",list(names),format_func=lambda i:names[i])
        selected_lot=next(lot for lot in open_lots if lot["índice"]==selected)
        st.write("**Último mês teórico de intervenção:** "+label(selected_lot["prazo"]))
        actions=["Manter lote","Reduzir 25%","Reduzir 50%","Cancelar lote","Aumentar 25%"]
        if selected+1<len(res["months"]):
            actions.append("Adiar 1 mês")
        if selected>0 and res["months"][selected-1]-res["ltm"]>close:
            actions.append("Antecipar 1 mês")
        choice=st.radio("Comparar alternativa",actions,horizontal=True,key="lot_action")
        plan=scenario_plan(res,selected,choice)
        if plan is not None:
            base_risk=impacts(res,product,res["production"],{"excesso":0,"ruptura":0})
            alternative=impacts(res,product,plan,base_risk)
            comparison=pd.DataFrame([
                {"Indicador":"Quantidade do lote (un.)","Plano atual":fmt(selected_lot["volume"]),
                 "Alternativa":fmt(plan[selected])},
                {"Indicador":"Risco de excesso em algum mês da janela","Plano atual":f'{base_risk["excesso"]:.1%}',
                 "Alternativa":f'{alternative["excesso"]:.1%}'},
                {"Indicador":"Risco de ruptura em algum mês da janela","Plano atual":f'{base_risk["ruptura"]:.1%}',
                 "Alternativa":f'{alternative["ruptura"]:.1%}'},
                {"Indicador":"Prazo teórico","Plano atual":label(selected_lot["prazo"]),
                 "Alternativa":label(selected_lot["prazo"])},
            ])
            st.subheader("Plano atual × alternativa")
            st.dataframe(comparison,hide_index=True,use_container_width=True)
            st.caption("As probabilidades representam risco em pelo menos um mês da janela, não o maior percentual mensal. As alternativas usam exatamente as mesmas 1.000 trajetórias de demanda.")
            st.warning("Cenário matemático, não autorização de alteração. Confirme contratos, capacidade, insumos e lotes mínimos antes de agir.")
        else:
            st.warning("Esta ação não cabe no horizonte de planejamento disponível.")

elif page == "Validação histórica dos alertas":
    st.title("Validação histórica dos alertas")
    st.write("O que o Smart Launch previa em cada fechamento, o que foi registrado posteriormente e se o fornecedor ainda poderia receber uma alteração.")
    st.info(
        "Esta é uma **reconstrução retrospectiva** com as revisões do Triângulo, "
        "não uma auditoria de alertas efetivamente salvos no passado. "
        "A aplicação ainda não guarda as previsões emitidas e os modelos aprovados em cada fechamento."
    )
    st.caption(
        "A previsão e as probabilidades são recalculadas usando somente a revisão da origem. "
        "Os realizados futuros entram apenas na verificação, nunca na previsão original."
    )
    v1,v2,v3=st.columns([1,1,1])
    with v1:
        product=st.selectbox("Produto",list(MODEL),index=list(MODEL).index(chosen),key="validation_product")
    last_close=latest_verifiable_close(blocks,product)
    selectable=[rev-1 for rev in available_origin_reviews(blocks,product,last_close)] if last_close is not None else []
    if not selectable:
        st.warning("Não existem revisões históricas suficientes para avaliar este produto.")
        st.stop()
    with v2:
        verification_close=st.selectbox(
            "Verificar com dados até",selectable,index=len(selectable)-1,
            format_func=label,key="validation_asof"
        )
    with v3:
        max_origins=st.selectbox(
            "Fechamentos reconstruídos",[4,8,12,24],index=1,key="validation_origins"
        )
    horizon=st.select_slider("Horizonte máximo por previsão (meses)",[3,6,9,12],value=9,
                            key="validation_horizon")
    initial_model=MODEL[product]
    chosen_operational=st.session_state["operational_"+product]
    model_choices=[initial_model]
    if chosen_operational!=initial_model:
        model_choices.append(chosen_operational)
    model=st.selectbox("Modelo para reconstruir as previsões",model_choices,
                       key="validation_model")
    st.caption(
        "Modelo congelado para fins de comparação. Caso a seleção do modelo tenha mudado "
        "ao longo dos meses, este histórico não recupera automaticamente a escolha feita à época."
    )
    with st.spinner("Reconstituindo fechamentos históricos sem usar dados futuros na previsão..."):
        projections, alerts, gaps=reconstruct_history(
            product, verification_close, blocks, base, model=model,
            max_origins=max_origins, max_horizon=horizon,
            method=DEFAULT_METHOD, persistent=False
        )
    earliest=first_alerts(alerts)
    verified=(
        earliest[earliest["Status observado"].isin([EVENT_YES, EVENT_NO])]
        if not earliest.empty else earliest
    )
    confirmed=(verified["Status observado"]==EVENT_YES).sum() if not verified.empty else 0
    false_alarms=(verified["Status observado"]==EVENT_NO).sum() if not verified.empty else 0
    timely=int(earliest["Emitido em tempo pelo LT"].sum()) if not earliest.empty else 0
    metrics=st.columns(4)
    metrics[0].metric("Primeiros alertas",len(earliest))
    metrics[1].metric("Excessos verificáveis",int(confirmed) if len(verified) else "—")
    metrics[2].metric("Alertas de excesso não confirmados",int(false_alarms) if len(verified) else "—")
    metrics[3].metric("Alertas com prazo teórico aberto",timely if not earliest.empty else "—")
    st.caption(
        "Os resultados contam **meses-alvo × tipo de risco distintos**, usando a primeira emissão "
        "para evitar contabilizar o mesmo problema repetido em revisões sobrepostas. "
        "Status de excesso só é verificável se o estoque estiver registrado e a demanda futura "
        "realizada permitir decidir o limite de 180 dias. Prazo aberto pelo LT não confirma "
        "possibilidade contratual de alteração."
    )
    st.subheader("Primeiro alerta por mês-alvo")
    if earliest.empty:
        st.warning(
            "Nenhum alerta probabilístico pôde ser reconstruído nas revisões selecionadas. "
            "Isso não significa ausência de excesso ou ruptura."
        )
    else:
        status_cols=[
            "Fechamento","Mês-alvo","Tipo de alerta","Probabilidade do alerta (%)",
            "Previsão no fechamento (un.)","Venda realizada (un.)",
            "Estoque na revisão posterior (un.)","Cobertura com realizados",
            "Status observado","Antecedência (meses)",
            "Próximo prazo","Status de oportunidade"
        ]
        st.dataframe(earliest[status_cols],hide_index=True,use_container_width=True)
        st.caption(
            "A classificação de ruptura permanece não verificável enquanto não houver "
            "dados de vendas perdidas efetivamente realizadas. Estoque zerado, isoladamente, "
            "não prova demanda não atendida."
        )
    st.subheader("Previsão original reconstruída × realizado")
    if projections.empty:
        st.warning("Não existem previsões históricas reconstruíveis com os critérios atuais.")
    else:
        st.caption(
            "O erro percentual só é calculado quando existe venda realizada positiva. "
            "O estoque é o valor da coluna do mês-alvo na revisão seguinte (m+1), "
            "não o estoque projetado na data do alerta."
        )
        shown=[
            "Fechamento","Mês-alvo","Horizonte","Modelo reconstruído",
            "Previsão no fechamento (un.)","Venda realizada (un.)",
            "Erro absoluto (un.)","Erro percentual (%)",
            "Estoque na revisão posterior (un.)",
            "Cobertura com realizados","Verificação de excesso",
            "Prob. excesso (%)","Prob. ruptura (%)"
        ]
        st.dataframe(projections[shown],
                     hide_index=True,use_container_width=True)
        s1,s2=st.columns(2)
        with s1:
            if not alerts.empty:
                target_options=sorted(set(alerts["_alvo"]))
            else:
                target_options=sorted(set(projections["_alvo"]))
            selected_target=st.selectbox("Acompanhar um mês-alvo",target_options,format_func=label)
        with s2:
            chart_type=st.selectbox("Tipo de probabilidade",["Excesso","Ruptura"])
        chart_source=projections[projections["_alvo"]==selected_target].sort_values("_origem")
        risk_col="Prob. excesso (%)" if chart_type=="Excesso" else "Prob. ruptura (%)"
        chart_source=chart_source.dropna(subset=[risk_col])
        if not chart_source.empty:
            fchart=go.Figure()
            fchart.add_trace(go.Scatter(
                x=chart_source["Fechamento"],y=chart_source[risk_col],
                name=chart_type,mode="lines+markers",
                line=dict(color="#b42318" if chart_type=="Excesso" else "#d69b14",width=3)
            ))
            fchart.add_hline(y=2.5,line_dash="dash",line_color="#595959",
                             annotation_text="Gatilho 2,5%",annotation_position="top left")
            fchart.update_layout(template="plotly_white",height=295,
                                 yaxis_title="Probabilidade (%)",
                                 xaxis_title="Fechamento da previsão",
                                 margin=dict(l=20,r=15,t=24,b=15),showlegend=False)
            st.plotly_chart(fchart,use_container_width=True)
        else:
            st.info("Este mês-alvo ainda não tem probabilidades históricas válidas.")
    if not alerts.empty:
        with st.expander("Todas as emissões históricas, inclusive alertas repetidos"):
            detail_cols=[
                "Fechamento","Mês-alvo","Tipo de alerta",
                "Probabilidade do alerta (%)","Status observado",
                "Status de oportunidade","Antecedência (meses)"
            ]
            st.dataframe(alerts[detail_cols],hide_index=True,use_container_width=True)
    if not gaps.empty:
        with st.expander("Fechamentos sem previsão ou sem simulação completa"):
            st.dataframe(gaps,hide_index=True,use_container_width=True)
    st.subheader("Exportar validação")
    left,right=st.columns(2)
    if not projections.empty:
        csv_projection=projections.drop(columns=["_origem","_alvo"]).to_csv(
            index=False
        ).encode("utf-8-sig")
        left.download_button(
            "Baixar previsões × realizados (CSV)",csv_projection,
            file_name="validacao_previsoes_"+product+".csv",mime="text/csv"
        )
    if not earliest.empty:
        csv_alerts=earliest.drop(columns=["_origem","_alvo"]).to_csv(
            index=False
        ).encode("utf-8-sig")
        right.download_button(
            "Baixar primeiros alertas (CSV)",csv_alerts,
            file_name="validacao_alertas_"+product+".csv",mime="text/csv"
        )
    st.warning(
        "Validação exploratória. As probabilidades foram geradas com poucos erros históricos "
        "e não têm calibração comprovada. Sem seis meses futuros realizados (ou esgotamento "
        "observado antes disso), não é correto declarar excesso confirmado ou descartado. "
        "O estoque apresentado é um registro de revisão posterior cujo significado "
        "operacional deve ser confirmado com a L'Oréal."
    )

elif page == "Histórico e metodologia":
    st.title("Histórico e metodologia")
    st.write("Parâmetros, rastreabilidade e limitações do Smart Launch.")
    st.subheader("Registro desta sessão")
    st.caption("Fechamento "+label(close)+" · Arquivo "+file_name)
    approvals=st.session_state.get("approvals",[])
    if approvals:
        st.dataframe(pd.DataFrame(approvals),hide_index=True,use_container_width=True)
    else:
        st.info("Nenhuma mudança de modelo aprovada nesta sessão.")
    st.warning("Registros não persistem entre sessões. Não representam trilha de auditoria empresarial.")
    st.subheader("Premissas de simulação")
    st.selectbox("Distribuição de erros",["Normal (0, s)","Bootstrap centralizado"],key="simulation_method")
    st.checkbox("Erro persistente entre meses (sensibilidade)",key="simulation_persistent")
    st.markdown("""
**Método principal do TCC:** previsão por analogia MEA / MEA-P ou plano Oficial,
erro aditivo Normal(0,s), 1.000 trajetórias, estoque com vendas perdidas e
cobertura pelo consumo futuro. Excesso se cobertura ≥ 180 dias, ruptura se
venda perdida > 0. Os alertas são aplicados apenas dentro da janela crítica
e quando o evento supera o limite de 2,5% dos cenários.

**Janela crítica:** teto(lead time em semanas × 7/30) +
teto(cobertura-alvo / 30) + 1 mês.

**Limitações:** poucos erros de arranque, previsões históricas sobrepostas,
distribuição Normal não comprovada e restrições operacionais de fornecedor
não incorporadas. A regra de seleção de modelos da aba Previsão é uma
versão reduzida experimental e precisa de homologação.
""")
    export=[]
    for product,res in results.items():
        if res is not None:
            frame=rows_from_sim(res)
            frame.insert(0,"Produto",product)
            export.append(frame.drop(columns=["Período"]))
    if export:
        data_csv=pd.concat(export,ignore_index=True).to_csv(index=False).encode("utf-8-sig")
        st.download_button("Exportar riscos do fechamento (CSV)",data_csv,
                           file_name="smartlaunch_"+label(close).replace("/","-")+".csv",
                           mime="text/csv")
    st.caption("Dados confidenciais não são publicados no GitHub. Implantação empresarial requer autenticação, armazenamento privado, homologação dos cálculos e política de retenção.")
