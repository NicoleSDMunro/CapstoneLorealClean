"""Semáforo e simulador orientados à prevenção do excesso de estoque."""
import html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from smartlaunch_semaforo import (
    CORES, LEGENDA, _lab, cor_do_produto, lotes_alteraveis,
    semaforo, semaforo_cenario, vies_persistente,
)
from smartlaunch_linha_tempo import linha_do_tempo, CODIGO
from smartlaunch_impact import simulate_monthly_scenario, tcc_lot_limits


def _fmt(x):
    try:
        return f"{float(x):,.0f}".replace(",", ".") if np.isfinite(float(x)) else "—"
    except (TypeError, ValueError):
        return "—"


def cartao(linha, titulo=None, compacto=False):
    cor = CORES[linha["cor"]]
    chance = f"{linha['chance_max']:.0%}" if np.isfinite(linha["chance_max"]) else "—"
    meses = linha["meses_sinal"] or "nenhum mês"
    texto = (
        f'<div style="border-left:7px solid {cor["hex"]};background:{cor["fundo"]};'
        f'border-radius:11px;padding:12px 15px;margin:6px 0">'
        f'<div style="font-size:.78rem;color:#526477;text-transform:uppercase">'
        f'{html.escape(titulo or linha["tipo"])}</div>'
        f'<div style="font-weight:750;font-size:1.08rem;color:{cor["hex"]}">'
        f'● {cor["rotulo"]} <span style="font-weight:450;color:#33414f;font-size:.9rem">'
        f'· {html.escape(linha["nivel"])} · chance máx. {chance} · {html.escape(meses)}'
        f'</span></div>'
    )
    if not compacto:
        texto += (
            f'<div style="margin-top:6px;color:#253646"><b>Encaminhamento:</b> '
            f'{html.escape(linha["acao"])}</div>'
            f'<div style="color:#526477;font-size:.9rem;margin-top:4px"><b>Motivo:</b> '
            f'{html.escape(linha["porque"])}</div>'
            f'<div style="color:#33414f;margin-top:7px;font-size:.88rem">'
            f'<b>Quem conduz:</b> {html.escape(linha.get("decisor","—"))} · '
            f'<b>Até quando:</b> {html.escape(linha.get("ate","—"))}</div>'
        )
    st.markdown(texto + "</div>", unsafe_allow_html=True)


def legenda():
    with st.expander("Como o semáforo decide a cor"):
        for cor, titulo, descricao in LEGENDA:
            dados = CORES[cor]
            st.markdown(
                f'<span style="color:{dados["hex"]};font-weight:750">● {html.escape(titulo)}</span>'
                f' — {html.escape(descricao)}', unsafe_allow_html=True
            )
        st.caption(
            "Chance de excesso em cobertura ≥180 dias, nos meses avaliáveis da janela crítica. "
            "Aviso >2,5%; alerta >20% (limiares exploratórios do TCC). "
            "O prazo é mês do lote menos lead time, em meses, e depende de confirmação "
            "dos contratos e da data de corte do fornecedor. Nenhuma cor aprova um corte. "
            "Papéis de Supply, Demanda e Comercial são sugestões, a validar com a L’Oréal."
        )


def semaforo_resumo(res, close, produto):
    linhas = semaforo(res, close)
    principal = next(l for l in linhas if l["tipo"] == "excesso")
    c = CORES[principal["cor"]]
    st.markdown(
        f'**Excesso de estoque · {html.escape(produto)}:** '
        f'<span style="font-weight:750;color:{c["hex"]}">● {c["rotulo"]}</span>',
        unsafe_allow_html=True,
    )
    cartao(principal, "Risco principal · excesso de estoque")
    secundario = next(l for l in linhas if l["tipo"] == "ruptura")
    if secundario["cor"] != "cinza":
        with st.expander("Restrição complementar: risco de ruptura"):
            cartao(secundario, "Risco de ruptura")
    with st.expander("Diagnóstico complementar: viés da previsão", expanded=False):
        cartao_vies(res)
    legenda()
    return linhas


def pagina(res, close, produto, blocks=None, base=None):
    st.subheader("Recebi um alerta de excesso. O que posso fazer?")
    st.caption(
        f"Produto {produto} · fechamento {_lab(close)} · lead time {int(res['ltm'])} meses · "
        "cenários originais e modificados com as mesmas trajetórias de demanda."
    )
    st.markdown("#### 1. Alerta, urgência e responsável")
    antes = semaforo_resumo(res, close, produto)

    st.markdown("#### 2. Quais lotes de produção ainda posso analisar?")
    active = np.asarray(res["active"], bool)
    lotes = [
        l for l in lotes_alteraveis(res["months"], res["production"], res["ltm"], close)
        if active[l["indice"]]
    ]
    if not lotes:
        st.warning(
            "Não há lotes positivos com prazo teórico futuro na janela crítica. "
            "Não é possível simular cortes de fornecedor neste fechamento. "
            "Avaliar estoque já existente e alternativas comerciais com a L’Oréal."
        )
        if blocks is not None and base is not None:
            linha_do_tempo_ui(produto, close, blocks, base, model=res.get("model"))
        return
    linhas = []
    for l in lotes:
        lim = tcc_lot_limits(res, l["indice"])
        linhas.append({
            "Índice": l["indice"], "Lote": _lab(l["mes"]),
            "Produção original (un.)": l["unidades"],
            "Prazo teórico": _lab(l["prazo"]),
            "Meses até o prazo": l["meses_ate_prazo"],
            "Corte seguro individual (%)": float(lim["max_cut_pct"]),
            "Corte seguro individual (un.)": float(lim["max_cut_units"]),
        })
    base = pd.DataFrame(linhas)
    st.dataframe(
        base.drop(columns="Índice").style.format({
            "Produção original (un.)": _fmt,
            "Corte seguro individual (%)": "{:.0f}%",
            "Corte seguro individual (un.)": _fmt,
        }),
        hide_index=True, use_container_width=True,
    )
    st.caption(
        "Os limites individuais reproduzem a regra exploratória do TCC (cortes em passos de 5%). "
        "Combinar vários cortes não garante que a combinação também passe: ela será simulada novamente. "
        "A elegibilidade pelo lead time não verifica lote mínimo nem contrato."
    )

    st.markdown("#### 3. Compare cortes possíveis")
    opcoes = [
        "Plano original", "Maior corte individual no lote de prazo mais próximo",
        "Combinar cortes individuais", "Personalizado",
    ]
    chave = f"sem_{produto}_{_lab(close)}"
    escolha = st.radio("Cenário para comparar", opcoes, key=chave+"_modo", horizontal=True)
    primeiro = min(lotes, key=lambda l: l["prazo"])["indice"]
    original = np.asarray(res["production"], float)
    if escolha == opcoes[0]:
        mudancas = [0.0 for _ in linhas]
    elif escolha == opcoes[1]:
        mudancas = [
            -row["Corte seguro individual (%)"] if row["Índice"] == primeiro else 0.0
            for row in linhas
        ]
    elif escolha == opcoes[2]:
        mudancas = [-row["Corte seguro individual (%)"] for row in linhas]
    else:
        mudancas = [0.0 for _ in linhas]

    editavel = base[["Índice", "Lote", "Produção original (un.)", "Prazo teórico"]].copy()
    editavel["Alteração (%)"] = mudancas
    if escolha == opcoes[3]:
        editavel = st.data_editor(
            editavel, key=chave+"_editor", hide_index=True,
            disabled=["Índice", "Lote", "Produção original (un.)", "Prazo teórico"],
            num_rows="fixed", use_container_width=True,
            column_config={
                "Índice": None,
                "Alteração (%)": st.column_config.NumberColumn(
                    "Alteração (%) · negativo = corte",
                    min_value=-100, max_value=200, step=5.0, format="%.0f",
                ),
            },
        )
    else:
        st.dataframe(
            editavel.drop(columns="Índice").style.format({
                "Produção original (un.)": _fmt, "Alteração (%)": "{:+.0f}%",
            }),
            hide_index=True, use_container_width=True,
        )
    plano = original.copy()
    for _, r in editavel.iterrows():
        j = int(r["Índice"])
        plano[j] = max(0.0, original[j] * (1.0 + float(r["Alteração (%)"])/100.0))
    analise = simulate_monthly_scenario(res, plano)
    depois = semaforo_cenario(res, close, plano, analise)

    st.markdown("#### 4. Impacto sobre o excesso de estoque")
    col_ant, col_dep = st.columns(2)
    with col_ant:
        st.markdown("**Plano original**")
        cartao(antes[0], "Excesso de estoque", compacto=True)
    with col_dep:
        st.markdown("**Plano simulado**")
        cartao(depois[0], "Excesso de estoque", compacto=True)
    original_kpi = analise["original"]
    sim_kpi = analise["simulated"]
    diferenca = analise["delta"]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        "Excedente no pior mês", _fmt(sim_kpi["Excedente no pior mês (un.)"])+" un.",
        _fmt(diferenca["Excedente no pior mês (un.)"])+" un.",
        delta_color="inverse",
    )
    k2.metric(
        "Produção retirada", _fmt(original.sum()-plano.sum())+" un."
    )
    k3.metric(
        "Vendas perdidas na janela", _fmt(sim_kpi["Vendas perdidas na janela (un.)"])+" un.",
        _fmt(diferenca["Vendas perdidas na janela (un.)"])+" un.",
        delta_color="inverse",
    )
    k4.metric(
        "Fill rate", f'{sim_kpi["Fill rate (%)"]:.1f}%',
        f'{diferenca["Fill rate (%)"]:+.1f} p.p.',
    )

    mudou = bool(analise["changed_lots"] > 0)
    passa = (not analise["new_rupture_signal"] and analise["max_rupture_rise_pp"] <= 2.5)
    st.markdown("**Avaliação exploratória da alternativa**")
    if not mudou:
        st.info("Plano mantido. Selecione um corte para comparar seu efeito no excesso.")
    elif passa:
        st.success(
            "A alternativa passa na restrição exploratória de ruptura do TCC. "
            "Isso não garante uma economia nem autoriza cancelar o pedido. "
            "Confirmar volumes, data de corte, contrato e lotes mínimos com o planejador."
        )
    else:
        st.warning(
            "A alternativa reduz estoque, mas não passa na restrição exploratória de ruptura: "
            "pode criar novo alerta ou aumentar a chance mensal acima de 2,5 p.p. "
            "Considere reduzir o corte."
        )
    mensal = analise["monthly"].copy()
    mensal["Mês"] = [_lab(m) for m in res["months"]]
    mensal = mensal[mensal["Janela crítica"]]
    colunas = [
        "Mês", "Produção original (un.)", "Produção simulada (un.)",
        "Excesso atual (%)", "Excesso simulado (%)",
        "Ruptura atual (%)", "Ruptura simulada (%)",
        "Cobertura atual P50 (dias)", "Cobertura simulada P50 (dias)",
    ]
    st.dataframe(
        mensal[colunas].style.format(
            {k: _fmt for k in ["Produção original (un.)", "Produção simulada (un.)",
                              "Cobertura atual P50 (dias)", "Cobertura simulada P50 (dias)"]}
            | {k: "{:.1f}%" for k in ["Excesso atual (%)", "Excesso simulado (%)",
                                    "Ruptura atual (%)", "Ruptura simulada (%)"]},
            na_rep="—",
        ),
        use_container_width=True, hide_index=True,
    )
    st.caption(
        "Resultado contrafactual com as mesmas 1.000 trajetórias, não economia realizada. "
        "Alterações não são aplicadas ao Triângulo nem a pedidos no ERP."
    )
    if blocks is not None and base is not None:
        linha_do_tempo_ui(produto, close, blocks, base, model=res.get("model"))


def faixa_produtos(results, close):
    """Resumo por produto; excesso como prioridade e ausência de simulação explícita."""
    partes = []
    for produto, res in results.items():
        if res is None:
            partes.append(
                f'<span style="color:#6B7785;margin-right:20px">● {html.escape(produto)} · sem simulação</span>'
            )
            continue
        linhas = semaforo(res, close)
        exc = next(l for l in linhas if l["tipo"] == "excesso")
        c = CORES[exc["cor"]]
        partes.append(
            f'<span style="color:{c["hex"]};font-weight:700;margin-right:20px">'
            f'● {html.escape(produto)} · {c["rotulo"]}</span>'
        )
    st.markdown(
        '<div style="background:white;border:1px solid #dfe6ee;border-radius:11px;'
        'padding:12px 15px;margin:5px 0 14px">'
        '<span style="color:#4b5866;margin-right:18px">Semáforo de excesso</span>'
        + "".join(partes) + "</div>", unsafe_allow_html=True,
    )
