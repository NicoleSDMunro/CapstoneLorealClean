"""Desktop-first Smart Launch executive decision surface.

The view never invents sample KPIs: it reads the same forecast, risk and inventory
arrays already computed by smartlaunch_core. Planner approval remains external.
"""
import html
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from smartlaunch_core import LIM, N, AVISO, ALERTA, label, known, forecast, MODEL, SHEETS
from smartlaunch_priority import card_summary
from smartlaunch_supply import future_lots, supply_diagnosis
from smartlaunch_impact import (
    editable_lots, outcome_metrics, evaluate_lot_options, tcc_check,
    historical_mape_vs_official,
)
from smartlaunch_visuals import forecast_figure


EXECUTIVE_CSS = """
<style>
/* Desktop layout: real dashboard width rather than a narrow article. */
@media(min-width: 1024px){
  .block-container{max-width:1840px!important;padding-top:1.05rem!important;
      padding-left:2.2rem!important;padding-right:2.2rem!important;}
}
.stApp{background:#F4F7FB!important;color:#102A43;}
[data-testid="stSidebar"]{background:#102A43!important;border-right:1px solid #24455f!important;}
[data-testid="stSidebar"] *{color:#e8f0fb;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#dce7f7;}
[data-testid="stSidebar"] .stRadio label{color:#e8f0fb;}
[data-testid="stSidebar"] div[data-baseweb="select"] *{color:#102A43;}
[data-testid="stHeader"]{background:#F4F7FB!important;}
h1{font-size:2rem!important;letter-spacing:-.035em!important;margin-bottom:.2rem!important;}
h2,h3{letter-spacing:-.03em!important;color:#102A43!important;}
[data-testid="stMetric"]{background:#fff;border:1px solid #e2e9f3;
  border-radius:12px!important;padding:10px 16px!important;min-height:102px;
  box-shadow:none!important;}
[data-testid="stMetricLabel"]{color:#536881!important;font-size:.82rem!important;}
[data-testid="stMetricValue"]{font-size:1.72rem!important;font-weight:760!important;
  color:#102A43!important;line-height:1.1!important;}
[data-testid="stMetricDelta"]{font-size:.75rem!important;}
[data-testid="stVerticalBlockBorderWrapper"]>div{border:1px solid #e2e9f3!important;
  border-radius:13px!important;box-shadow:none!important;}
[data-testid="stPlotlyChart"]{border:0!important;}
.stButton button{border-radius:8px!important;min-height:37px!important;}
.stButton button[kind="primary"]{background:#2563EB!important;border-color:#2563EB!important;}
.sl-kicker{font-size:11px;font-weight:800;letter-spacing:.11em;color:#4f6a88;margin:0;}
.sl-reco{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(210px,.7fr);
  gap:18px;align-items:center;background:#102A43;color:white;padding:17px 22px;
  border-radius:13px;margin:7px 0 8px;}
.sl-reco .sl-tag{font-size:10px;letter-spacing:.11em;font-weight:800;color:#a6cafa;}
.sl-reco h2{color:white!important;margin:5px 0!important;font-weight:790!important;
  font-size:1.38rem!important;line-height:1.2;}
.sl-reco p{font-size:.87rem;line-height:1.5;color:#dce9f7;margin:5px 0;}
.sl-reco .sl-response{border-left:1px solid #50718a;padding-left:19px;}
.sl-reco .sl-response h3{font-size:1.02rem!important;color:#fff!important;margin:7px 0;}
.sl-reco .sl-response small{color:#bed0e5;font-size:.77rem;}
.sl-process{font-size:11px;color:#5a708a;letter-spacing:.015em;padding:3px 2px 8px;}
.sl-process b{color:#173858;font-weight:780;}
.sl-section{font-size:13px!important;text-transform:uppercase;letter-spacing:.07em;
  font-weight:780!important;color:#102A43;padding-top:4px;margin:0;}
.sl-panel{background:#fff;border:1px solid #e1e9f2;border-radius:12px;padding:9px 12px 1px;}
.sl-panel-title{font-size:12px;font-weight:780;color:#102A43;letter-spacing:.035em;
  padding:2px 0 0;}
.sl-note{font-size:11px;line-height:1.5;color:#61758f;margin:2px 0 8px;}
.sl-subline{display:flex;gap:14px;flex-wrap:wrap;color:#546b84;font-size:12px;padding:3px 1px 9px;}
.sl-step{background:#fff;border:1px solid #e1e9f2;border-radius:12px;
  padding:14px 17px;min-height:90px;margin:4px 0;}
.sl-step strong{color:#102A43;}
.sl-step small{color:#586f88;font-size:12px;line-height:1.5;}
.sl-safe{background:#effaf3;color:#166b3e;padding:4px 8px;border-radius:6px;font-size:11px;}
.sl-exploratory{background:#fff8e8;color:#936316;padding:4px 8px;border-radius:6px;font-size:11px;}
@media(max-width:1050px){
  .sl-reco{grid-template-columns:1fr;}
  .sl-reco .sl-response{border-left:0;border-top:1px solid #50718a;padding:12px 0 0;}
}
</style>
"""


def _number(v):
    return "—" if v is None or not np.isfinite(v) else f"{v:,.0f}".replace(",", ".")


def _percent(v):
    return "—" if v is None or not np.isfinite(v) else f"{float(v):.1f}%".replace(".", ",")


def _future(res, horizon):
    total = len(res["months"])
    return min(total, 3 if horizon == "3M" else 6 if horizon == "6M" else total)


def _risk_frame(res, count):
    meses = res["months"][:count]
    active = np.asarray(res["active"][:count], dtype=bool)
    evaluated = np.asarray(res.get("evaluated", np.ones(len(res["months"]), bool))[:count], dtype=bool)
    ex = np.mean(np.asarray(res["cov"][:, :count]) >= LIM, axis=0)*100
    ru = np.mean(np.asarray(res["lost"][:, :count]) > 0, axis=0)*100
    ex[~evaluated] = np.nan
    return pd.DataFrame({"Mês":[label(m) for m in meses],
                         "Período":months, "Excesso":ex, "Ruptura":ru,
                         "Crítica":active, "Avaliável":evaluated})


def _risk_plot(frame):
    chart=go.Figure()
    for col, color in (("Excesso","#DC2626"),("Ruptura","#F59E0B")):
        chart.add_trace(go.Bar(
            x=frame["Mês"],y=frame[col],name=col,
            marker_color=color,opacity=.88,
            hovertemplate="%{x}<br>"+col+": %{y:.1f}%<extra></extra>"
        ))
    chart.add_hline(y=20,line_color="#586c85",line_dash="dash",line_width=1,
                    annotation_text="Alerta >20%",annotation_font_size=10)
    chart.update_layout(
        template="plotly_white",height=225,barmode="group",hovermode="x unified",
        font=dict(color="#102A43",size=11),margin=dict(l=4,r=4,t=8,b=12),
        paper_bgcolor="#fff",plot_bgcolor="#fff",
        yaxis=dict(range=[0,105],title=None,ticksuffix="%",gridcolor="#eff3f8"),
        xaxis=dict(title=None,showgrid=False),legend=dict(orientation="h",y=1.18,x=0)
    )
    return chart


def _coverage_plot(res,count):
    xs=[label(m) for m in res["months"][:count]]
    values=[]
    for j in range(count):
        finite=res["cov"][:,j]
        finite=finite[np.isfinite(finite)]
        is_evaluated=bool(res.get("evaluated",np.ones(len(res["months"]),bool))[j])
        values.append(float(np.median(finite)) if len(finite) and is_evaluated else None)
    chart=go.Figure()
    chart.add_trace(go.Scatter(
        x=xs,y=values,mode="lines+markers",name="Cobertura futura mediana",
        line=dict(color="#2563EB",width=3),marker=dict(size=7),
        fill="tozeroy",fillcolor="rgba(37,99,235,.065)",
        hovertemplate="%{x}<br>Cobertura mediana: %{y:.0f} dias<extra></extra>"
    ))
    chart.add_hline(y=LIM,line_color="#DC2626",line_dash="dash",line_width=1.3,
                    annotation_text=str(LIM)+" dias · limite operacional",
                    annotation_position="top left",annotation_font_size=10)
    chart.update_layout(
        template="plotly_white",height=158,margin=dict(l=5,r=8,t=3,b=13),
        hovermode="x",showlegend=False,paper_bgcolor="#fff",plot_bgcolor="#fff",
        font=dict(color="#102A43",size=11),
        xaxis=dict(title=None,showgrid=False),
        yaxis=dict(title=None,gridcolor="#eff3f8",rangemode="tozero")
    )
    return chart


def _headline(summary,valid):
    if not valid:
        return "Simulação indisponível", "Revise os dados disponíveis antes de considerar qualquer ação", "Revisão do planejador necessária"
    if summary["alert"]:
        risk=summary["type"].lower()
        first=label(summary["first_month"])
        title="Alto risco de "+("excesso" if risk=="excesso" else "ruptura")+" identificado"
        if summary["first_target_has_changeable_lot"]:
            return title, ("Risco identificado para "+first+". Existe um lote de produção relevante com uma janela teórica para "
                           "alteração; confirme a data de corte com o fornecedor antes de comparar intervenções."), "Avaliar alternativas de abastecimento"
        if risk=="excesso":
            return title, ("Risco identificado para "+first+". Não há lote relevante alterável "
                           "dentro da janela teórica de lead time; avalie ações comerciais e mantenha o monitoramento."), "Ação comercial + monitoramento"
        return title, ("Risco identificado para "+first+". Não há lote relevante alterável "
                       "antes do evento; avalie a realocação e eventuais exceções com Supply Chain."), "Rever alocação e exceções"
    if summary.get("warning"):
        return "Aviso antecipado — acompanhar",("Aviso baseado no modelo para "+
                label(summary["warning_month"])+". Reavalie no próximo fechamento."),"Acompanhar próximo fechamento"
    return "Nenhum alerta na janela crítica", "Não houve alerta acima do limiar nos meses avaliados. Continue o monitoramento mensal.", "Manter monitoramento"


def _decision_trail(summary, res, close, count):
    if not summary or res is None: return
    st.markdown("#### POR QUE ESSA RECOMENDAÇÃO?")
    lots=future_lots(res,close)
    lead=int(res["ltm"])
    peak = summary.get("peak_probability") if summary.get("alert") else summary.get("warning_probability")
    if summary.get("alert"):
        first=label(summary["first_month"])
        month=summary["first_month"]
        usable=[x for x in lots if x["month"]<=month and x["available_for_analysis"]]
        deadline=label(summary["deadline"]) if summary["deadline"] is not None else "—"
        assessment=("Janela teórica de alteração para "+str(len(usable))+" lote(s)"
                    if usable else "Nenhum lote relevante alterável antes do primeiro risco")
        rows=[
            ("01 / RISCO", summary["type"]+" · "+_percent(100*peak), "Probabilidade condicional simulada, sem calibração comprovada."),
            ("02 / MOMENTO", first,"Primeiro alerta acima do limiar na janela crítica."),
            ("03 / POSSIBILIDADE DE AÇÃO", assessment,
             str(lead)+" mês(es) de lead time arredondado; mês-limite teórico "+deadline+". Confirmação do fornecedor necessária."),
            ("04 / ALTERNATIVAS", "Avaliar medidas de abastecimento e comerciais",
             "Compare intervenções apenas quando houver lotes relevantes ainda dentro da janela teórica."),
            ("05 / EQUILÍBRIO ENTRE RISCOS", "Excesso evitado versus vendas perdidas",
             "Compare taxa de atendimento, risco de ruptura e estoque com os mesmos cenários de demanda."),
            ("06 / RECOMENDAÇÃO", _headline(summary,True)[2],
             "Revisão do planejador necessária before any operational change."),
        ]
    else:
        rows=[
            ("01 / RISCO","Sem sinal de risco crítico","Nenhum alerta acima do gatilho exploratório de 20%."),
            ("02 / MOMENTO","Próximo fechamento mensal","Acompanhe as mudanças conforme a demanda real for conhecida."),
            ("03 / POSSIBILIDADE DE AÇÃO","Nenhuma intervenção proposta","Não apresente decisões sem evidências suficientes."),
            ("04 / ALTERNATIVAS","Manter plano / reavaliar","Examine alternativas apenas se surgirem novas evidências."),
            ("05 / EQUILÍBRIO ENTRE RISCOS","Monitorar atendimento e estoque","Não afirmar melhorias sem evidências."),
            ("06 / RECOMENDAÇÃO","Revisão do planejador necessária","A decisão final permanece com o planejador."),
        ]
    left,right=st.columns(2)
    for i,(stage,title,detail) in enumerate(rows):
        with (left if i%2==0 else right):
            st.markdown(
                '<div class="sl-step"><div class="sl-kicker">'+html.escape(stage)+
                '</div><strong>'+html.escape(title)+'</strong><br><small>'+
                html.escape(detail)+'</small></div>', unsafe_allow_html=True)


def render_executive_dashboard(
    product,close,blocks,results,errors,rankings,ready_count,horizon,mode,
    on_open_simulator,on_open_analytics
):
    """Risk → Timing → Actionability → Alternatives → Trade-off → Recommendation."""
    st.markdown(EXECUTIVE_CSS,unsafe_allow_html=True)
    res=results.get(product)
    summary=card_summary(product,res,close) if res is not None else None
    title,reason,response=_headline(summary,res is not None)
    caption=(f"{product} · Fechamento {label(close)} · "+
             ("Probabilidade condicional baseada em cenários simulados" if res is not None
              else "Probabilidade indisponível — faltam cenários simulados"))
    st.markdown('<div class="sl-reco"><div><div class="sl-tag">RECOMENDAÇÃO SMART LAUNCH · APOIO À DECISÃO</div>'+
                '<h2>'+html.escape(title)+'</h2><p>'+html.escape(reason)+
                '</p><p>'+html.escape(caption)+'</p></div>'+
                '<div class="sl-response"><div class="sl-tag">ENCAMINHAMENTO SUGERIDO</div>'+
                '<h3>'+html.escape(response)+'</h3><small>Revisão do planejador necessária<br>'+
                'Admissível apenas sob as premissas atuais</small></div></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="sl-process"><b>RISCO</b> &nbsp;→&nbsp; MOMENTO &nbsp;→&nbsp; '+
                'POSSIBILIDADE DE AÇÃO &nbsp;→&nbsp; ALTERNATIVAS &nbsp;→&nbsp; TRADE-OFF '+
                '&nbsp;→&nbsp; <b>RECOMENDAÇÃO</b></div>',unsafe_allow_html=True)
    if res is not None:
        supplier_window=("Primeiro risco: "+label(summary["first_month"]) if summary.get("alert")
                         else "Sem alerta crítico")
        supplier_deadline=("Mês-limite estimado do lote: "+label(summary["deadline"])
                           if summary.get("alert") and summary.get("deadline") is not None
                           else "Nenhum prazo de lote relevante")
        st.markdown('<div class="sl-subline"><span><b>'+html.escape(supplier_window)+
                    '</b></span><span>'+html.escape(supplier_deadline)+
                    '</span><span>Lead time do fornecedor: '+str(res["ltm"])+
                    ' meses arredondados</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="sl-section">INDICADORES EXECUTIVOS</div>',unsafe_allow_html=True)
    if res is None:
        st.info("O apoio à decisão está incompleto para "+product+": "+errors.get(product,"Erros históricos de previsão insuficientes")+
                ". Simulação indisponível não significa risco zero.")
        row=st.columns(5)
        for col,key in zip(row,("Risco de excesso","Cobertura mediana","Erro de previsão","Lotes com prazo teórico","Taxa de atendimento")):
            col.metric(key,"—")
        st.button("Ver evidências",on_click=on_open_analytics)
        return
    count=_future(res,horizon)
    whole=_risk_frame(res,len(res["months"]))
    critical=whole[whole["Crítica"]]
    ex=critical["Excesso"].dropna()
    ru=critical["Ruptura"].dropna()
    peak_ex=float(ex.max()) if len(ex) else None
    peak_ru=float(ru.max()) if len(ru) else None
    first_alert=summary.get("first_month") if summary.get("alert") else None
    risk_target=(res["months"].index(first_alert) if first_alert in res["months"]
                 else next((i for i,p in enumerate(res["months"])
                            if res["active"][i] and
                            res.get("evaluated",np.ones(len(res["months"]),bool))[i]),0))
    covers=np.asarray(res["cov"][:,risk_target],dtype=float)
    covers=covers[np.isfinite(covers)]
    median_cover=float(np.median(covers)) if len(covers) and bool(
        res.get("evaluated",np.ones(len(res["months"]),bool))[risk_target]) else None
    lots=future_lots(res,close)
    actionable=[x for x in lots if x["available_for_analysis"] and
                (first_alert is None or x["month"]<=first_alert)]
    detail=rankings[product][0] if product in rankings else pd.DataFrame()
    model=st.session_state.get("operational_"+product,MODEL[product])
    accuracy=historical_mape_vs_official(detail,model)
    try:
        outcomes=outcome_metrics(res,res["production"],risk_target)
        service=outcomes["fill_rate_pct"]
    except (ValueError,KeyError,IndexError):
        service=None
    cols=st.columns(5)
    cols[0].metric("Risco de excesso · pico",_percent(peak_ex),help="Maior probabilidade mensal simulada de excesso na janela crítica.")
    cols[1].metric("Cobertura mediana · primeiro risco",(_number(median_cover)+" d") if median_cover is not None else "—",
                   help="Cobertura futura mediana no primeiro mês com alerta ou no primeiro mês avaliável.")
    cols[2].metric("Erro de previsão · MAPE",_percent(accuracy["mape_operacional"]) if accuracy else "—",
                   help="MAPE histórico com pares comparáveis de origem e mês-alvo. Não é o resumo fixo do TCC.")
    cols[3].metric("Lotes com prazo teórico · teóricos",str(len(actionable)),help="Prazos estimados pelo lead time mensal arredondado; não representam autorização contratual.")
    cols[4].metric("Taxa de atendimento · simulada",_percent(service),help="Atendimento projetado nos cenários da janela crítica, não atendimento real observado.")
    if accuracy is not None:
        st.markdown('<div class="sl-subline"><span>MAPE oficial: <strong>'+
                    html.escape(_percent(accuracy["mape_oficial"]))+
                    '</strong></span><span>Comparações: '+str(accuracy["pares"])+
                    ' previsões comparáveis</span><span>Os modelos não são alterados automaticamente</span></div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="sl-subline">Erro de previsão unavailable for this closing; no comparative superiority is inferred.</div>',
                    unsafe_allow_html=True)

    st.markdown('<div class="sl-section">DEMANDA E RISCO PROJETADOS</div>',unsafe_allow_html=True)
    c1,c2=st.columns([1.65,1],gap="medium")
    with c1:
        st.markdown('<div class="sl-panel-title">PREVISÃO DE DEMANDA</div>',unsafe_allow_html=True)
        realized=known(blocks[SHEETS[product]]["PV"],close)
        meses=res["months"][:count]
        try:
            official=forecast(product,months,close,blocks,model="Oficial")
        except (ValueError,KeyError,IndexError,TypeError):
            official=None
        fig=forecast_figure(
            realized,months,res["center"][:count],official,res["dm"][:,:count],
            close,label,critical_count=min(res["window"],count),
            percentile_bounds=(2.5,97.5))
        fig.update_layout(height=231,margin=dict(l=10,r=8,t=7,b=35),
                          font=dict(color="#102A43",size=11),
                          legend=dict(orientation="h",y=-.27,x=0,font=dict(size=10)))
        for trace in fig.data:
            if trace.name=="Previsão em uso":trace.name="Smart Launch · "+model
            if trace.name=="Previsão Oficial":trace.line.color="#71849a"
        st.plotly_chart(fig,use_container_width=True)
    with c2:
        st.markdown('<div class="sl-panel-title">MONITOR DE RISCOS</div>',unsafe_allow_html=True)
        st.plotly_chart(_risk_plot(_risk_frame(res,count)),use_container_width=True)
    st.markdown('<div class="sl-subline"><span>Faixa de previsão: P2,5–P97,5 simulados, sem calibração comprovada</span>'+
                '<span>Risco = frequência condicional nos cenários</span>'+
                '<span>Alerta &gt;20%; aviso &gt;2,5% (limiares exploratórios)</span></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="sl-section">PROJEÇÃO DE COBERTURA DE ESTOQUE</div>',unsafe_allow_html=True)
    st.plotly_chart(_coverage_plot(res,count),use_container_width=True)
    st.markdown('<div class="sl-subline"><span>180 dias = limite operacional, não um corte estatístico universal</span>'+
                '<span>Cobertura não avaliável não significa risco zero</span>'+
                '<span>Estoque inicial: '+_number(float(res["e0"]))+' unidades</span>'+
                '<span>Lead time arredondado: '+str(res["ltm"])+' meses</span></div>',
                unsafe_allow_html=True)

    st.divider()
    st.markdown("### Simulador de decisões")
    st.caption("Detalhamento operacional · os mesmos "+str(N)+" cenários simulados de demanda em cada intervenção. "+
               "As mudanças são hipotéticas até validação do fornecedor, comercial e planejador.")
    editable=editable_lots(res,close)
    if not editable:
        st.info("Não há lote de produção teoricamente alterável neste fechamento. "
                +supply_diagnosis(res,close)["guidance"]+
                " Considere ação comercial e realocação de estoque; não simule o cancelamento de um lote inexistente.")
    else:
        preferred=next((x for x in editable if first_alert is not None and x["month"]<=first_alert),editable[0])
        a,b,c=st.columns([1,1,1.5])
        with a:
            lot_idx=st.selectbox("LOTE · mês de entrega",options=[x["index"] for x in editable],
                                 format_func=lambda i:label(res["months"][i]),
                                 index=[x["index"] for x in editable].index(preferred["index"]),
                                 key="exec_lot")
        with b:
            candidates=[i for i in range(len(res["months"]))
                        if res["active"][i] and res.get("evaluated",np.ones(len(res["months"]),bool))[i]]
            if candidates:
                target=st.selectbox("MÊS-ALVO",candidates,
                       index=candidates.index(risk_target) if risk_target in candidates else 0,
                       format_func=lambda i:label(res["months"][i]),key="exec_target")
            else:
                target=None
        with c:
            adjustment=st.slider("AJUSTE DO LOTE (%)",-100,50,0,5,key="exec_adjust",
                                 help="Mudança hipotética de volume; não cria nem altera ordens de produção.")
        lot=next(x for x in editable if x["index"]==lot_idx)
        st.caption("Mês-limite estimado: "+label(lot["deadline"])+
                   (" · mês-limite, data exata de corte não informada" if lot["boundary"] else
                    " · teóricos open window")+
                   ". É necessária a revisão do fornecedor e do planejador.")
        if target is None:
            st.warning("Nenhum mês-alvo avaliável disponível para comparar impactos.")
        else:
            baseline_plan=np.asarray(res["production"],dtype=float)
            plan=baseline_plan.copy()
            plan[lot_idx]=round(plan[lot_idx]*(1+adjustment/100))
            base_metrics=outcome_metrics(res,baseline_plan,target)
            alt_metrics=outcome_metrics(res,plan,target)
            check=tcc_check(res,plan)
            admissible=(not check["new_rupture"] and
                         check["max_rupture_rise"]<=.025 if adjustment<0 else
                         not check["new_excess"] if adjustment>0 else True)
            excess_avoided=base_metrics["expected_excess_units"]-alt_metrics["expected_excess_units"]
            additional_lost=alt_metrics["expected_lost_units"]-base_metrics["expected_lost_units"]
            v=st.columns(5)
            v[0].metric("Redução potencial de excesso",_number(excess_avoided)+" un.")
            v[1].metric("Vendas perdidas adicionais",_number(additional_lost)+" un.")
            v[2].metric("Taxa de atendimento · simulado",_percent(alt_metrics["fill_rate_pct"]))
            v[3].metric("Risco de excesso · mês-alvo",_percent(alt_metrics["risk_excess_target_pct"]),
                        delta=(f'{alt_metrics["risk_excess_target_pct"]-base_metrics["risk_excess_target_pct"]:+.1f} p.p.'),
                        delta_color="inverse")
            v[4].metric("Risco de ruptura · mês-alvo",_percent(alt_metrics["risk_rupture_target_pct"]),
                        delta=(f'{alt_metrics["risk_rupture_target_pct"]-base_metrics["risk_rupture_target_pct"]:+.1f} p.p.'),
                        delta_color="inverse")
            status=("Admissível sob as premissas atuais" if admissible else
                    "Não admissível sob as premissas atuais")
            st.caption(status+" · Revisão do planejador necessária. "+
                       "O lead time e os lotes mínimos do fornecedor podem impedir uma alteração teoricamente possível.")
            st.markdown("#### Alternativas de abastecimento · comparação de impactos")
            options,_=evaluate_lot_options(res,lot_idx,target)
            view=options[["Alternativa","Excesso potencialmente evitado (un.)",
                          "Vendas perdidas adicionais (un.)","Taxa de atendimento simulado (%)",
                          "Dentro do critério do TCC",
                          "Não dominada (excesso × perda)"]].copy()
            view["Status"]=np.where(view["Dentro do critério do TCC"],
                                    "Admissível sob as premissas atuais",
                                    "Não atende aos critérios simulados")
            view=view.drop(columns=["Dentro do critério do TCC"])
            st.dataframe(view,hide_index=True,use_container_width=True)
            no_lost=options[(options["Dentro do critério do TCC"])&
                            (options["Vendas perdidas adicionais (un.)"]<=1e-6)&
                            (options["Excesso potencialmente evitado (un.)"]>1e-6)]
            if not no_lost.empty:
                best=no_lost.sort_values("Excesso potencialmente evitado (un.)",ascending=False).iloc[0]
                st.caption("Melhor equilíbrio entre as alternativas *sem vendas perdidas adicionais*: "+
                           str(best["Alternativa"])+". Esta é uma comparação condicional "+
                           "das opções testadas, não uma decisão universal nem autorizada.")
            else:
                st.caption("Nenhuma redução admissível testada elimina totalmente o aumento esperado de vendas perdidas. "
                           "O planejador deve comparar todas as alternativas.")
            if base_metrics["extrapolated_months"]:
                st.caption("Excess unidades use an extrapolated six-month demand tail beyond the recorded horizon ("+
                           str(base_metrics["extrapolated_months"])+" mês(es)). Interprete como aproximação.")
        st.button("Abrir alternativas detalhadas e comparação de trade-offs",on_click=on_open_simulator)
    st.divider()
    st.markdown("### Por que usar o Smart Launch?")
    if mode=="Executivo":
        st.write("O Smart Launch acrescenta uma camada rastreável de apoio à decisão entre a previsão, "
                 "a exposição de estoque, o prazo do fornecedor e as ações avaliadas pelo planejador. "
                 "A ferramenta não executa nem aprova alterações na produção.")
    st.markdown("#### Antecipação dos alertas · resultados históricos do TCC")
    ea,eb,ec=st.columns(3)
    ea.metric("Smart Launch · alertas antes do lead time","2 / 3")
    eb.metric("Plano oficial · alertas antes do lead time","0 / 3")
    ec.metric("Precisão histórica dos alertas","48%")
    st.caption("Resultados fixos e retrospectivos do TCC, não recalculados a partir do Triângulo enviado. "+
               "Apenas três episódios observados de excesso; ainda sem validação prospectiva ou economia real demonstrada.")
    if mode!="Executivo":
        _decision_trail(summary,res,close,count)
    if mode=="Analista":
        st.markdown("### Qualidade das evidências e premissas do modelo")
        x=st.columns(4)
        x[0].metric("Integridade temporal","Reconstruída")
        x[1].metric("Escolhas de desenvolvimento","Exploratórias")
        x[2].metric("Precisão observada dos alertas · TCC","48%")
        x[3].metric("Validação prospectiva","Pendente")
        st.caption("O desenvolvimento dos casos P1–P3 do TCC orientou a MEA-P e o gatilho exploratório de 20%; "
                   "o valor de 48% pertence ao estudo histórico e não foi recalculado neste envio.")
        with st.expander("PREMISSAS DO MODELO · validação e limites"):
            st.markdown(
                "- Os erros históricos disponíveis são poucos e os riscos simulados não têm calibração comprovada.\n"
                "- A hipótese básica é Normal(0, s), salvo alteração na análise técnica.\n"
                "- Inventory coverage is forward-looking and uses a 180 dias · limite operacional.\n"
                "- Os prazos do fornecedor são aproximados em meses.\n"
                "- Não há evidência prospectiva de economia de estoque nem de decisões executadas.\n"
                "- Os resultados da MEA-P no desenvolvimento são exploratórios, não validação independente.\n"
                "- As comparações históricas parcialmente externas não constituem validação totalmente fora da amostra.\n"
                "- As decisões continuam sob responsabilidade do planejador."
            )
    st.button("Ver desempenho dos modelos, validação histórica e evidências",on_click=on_open_analytics)
