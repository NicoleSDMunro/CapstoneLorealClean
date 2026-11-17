"""Semáforo dos gatilhos: transformar alerta de excesso em prazo e possível ação.

Combina aviso >2,5%, alerta >20% e elegibilidade teórica dos lotes
(mês da entrega - lead time > fechamento). Sem alterar motor do TCC.
Não equivale a autorização do fornecedor.
"""
import numpy as np
import pandas as pd

AVISO, ALERTA = 0.025, 0.20
CORES = {
    "vermelho": dict(rotulo="Agir já", hex="#B3261E", fundo="#FBEAEA", ordem=3),
    "amarelo": dict(rotulo="Agir até o prazo", hex="#B7791F", fundo="#FFF6E0", ordem=2),
    "verde": dict(rotulo="Acompanhar", hex="#2E7D4F", fundo="#E8F5EC", ordem=1),
    "cinza": dict(rotulo="Sem sinal", hex="#6B7785", fundo="#F1F4F7", ordem=0),
}
LEGENDA = [
    ("vermelho", "Agir já",
     "Há alerta e a decisão não pode esperar. O prazo do lote útil é iminente ou não há lote alterável; nesse caso, analisar resposta comercial."),
    ("amarelo", "Agir até o prazo",
     "Há alerta, mas há tempo para avaliar as alternativas e negociar com o fornecedor."),
    ("verde", "Acompanhar",
     "Só aviso ou chance abaixo do alerta. Não cortar automaticamente a produção."),
]

def _lab(p):
    mes = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"][p.month-1]
    return f"{mes}/{str(p.year)[-2:]}"

def lotes_alteraveis(months, production, ltm, close):
    out = []
    for i, m in enumerate(months):
        q = float(production[i])
        deadline = m - int(ltm)
        if m > close and np.isfinite(q) and q > 0 and deadline > close:
            out.append(dict(indice=i, mes=m, unidades=q, prazo=deadline,
                            meses_ate_prazo=int((deadline-close).n)))
    return out

def classificar(months, active, evaluated, p_exc, p_rup, production, ltm, close):
    months = list(months)
    ativos = np.asarray(active, bool)
    aval = np.asarray(evaluated, bool)
    lotes = lotes_alteraveis(months, production, ltm, close)
    linhas = []
    for tipo, probs, validos in (
        ("excesso", np.asarray(p_exc, float), aval),
        ("ruptura", np.asarray(p_rup, float), np.ones(len(months), dtype=bool)),
    ):
        janela = [j for j in range(len(months))
                  if ativos[j] and validos[j] and np.isfinite(probs[j])]
        sinais = [j for j in janela if probs[j] > AVISO]
        if not sinais:
            linhas.append(dict(tipo=tipo, cor="cinza", nivel="sem sinal",
                               mes_sinal=None, chance_max=max((probs[j] for j in janela), default=np.nan),
                               meses_sinal="", prazo=None, lote=None, lotes_uteis=[],
                               acao="Acompanhar no próximo fechamento.",
                               porque="Nenhum mês avaliável da janela ultrapassou 2,5% de chance."))
            continue
        alertas = [j for j in sinais if probs[j] > ALERTA]
        nivel = "alerta" if alertas else "aviso"
        meses = alertas if alertas else sinais
        j0, ultimo = meses[0], max(meses)
        uteis = [l for l in lotes if l["indice"] <= ultimo]
        lote = min(uteis, key=lambda l:l["prazo"]) if uteis else None
        maxp = max(float(probs[j]) for j in sinais)
        meses_txt = ", ".join(_lab(months[j]) for j in sinais)
        verbo = "reduzir" if tipo == "excesso" else "revisar"
        if nivel == "aviso":
            cor = "verde"
            acao = "Acompanhar no próximo fechamento, sem mudar lotes apenas pelo aviso."
            porque = f"Maior chance: {maxp:.0%}; abaixo do alerta de 20%."
            if lote and lote["meses_ate_prazo"] <= 1:
                porque += f" Atenção ao prazo de {_lab(lote['mes'])}."
        elif lote is None:
            cor = "vermelho"
            acao = ("Consultar a área comercial: promoção, realocação entre canais ou antecipação de pedidos."
                    if tipo == "excesso" else
                    "Avaliar alocação do estoque disponível, priorizando pedidos firmes.")
            porque = f"Alerta em {_lab(months[j0])} sem lote positivo alterável até {_lab(months[ultimo])}."
        elif lote["meses_ate_prazo"] <= 1:
            cor = "vermelho"
            acao = (f"Solicitar avaliação de {verbo} o lote de {_lab(lote['mes'])} "
                    f"até {_lab(lote['prazo'])}; conferir prazo contratual.")
            porque = "Aguardar outro fechamento pode eliminar a janela de negociação."
        else:
            cor = "amarelo"
            acao = (f"Preparar proposta para {verbo} o lote de {_lab(lote['mes'])}, "
                    f"com decisão até {_lab(lote['prazo'])}.")
            porque = f"Há {lote['meses_ate_prazo']} meses até o prazo teórico; reavaliar no próximo fechamento."
        linhas.append(dict(tipo=tipo, cor=cor, nivel=nivel,
                           mes_sinal=months[j0], chance_max=maxp, meses_sinal=meses_txt,
                           prazo=lote["prazo"] if lote else None, lote=lote,
                           lotes_uteis=uteis, acao=acao, porque=porque))
    return linhas

def cor_do_produto(linhas):
    """Foco do estudo é excesso; risco de ruptura aparece como restrição complementar."""
    exc = next((l for l in linhas if l["tipo"] == "excesso"), None)
    if exc and exc["cor"] != "cinza":
        return exc["cor"]
    return max((l["cor"] for l in linhas), key=lambda c:CORES[c]["ordem"], default="cinza")

def semaforo(res, close):
    aval = np.asarray(res.get("evaluated", np.ones(len(res["months"]), bool)), bool)
    p_exc = np.where(aval, (np.asarray(res["cov"]) >= 180).mean(axis=0), np.nan)
    p_rup = (np.asarray(res["lost"]) > 0).mean(axis=0)
    return classificar(res["months"], res["active"], aval, p_exc, p_rup,
                      res["production"], res["ltm"], close)

def semaforo_cenario(res, close, plano, analise):
    m = analise["monthly"]
    return classificar(res["months"], res["active"],
                       res.get("evaluated", np.ones(len(res["months"]), bool)),
                       m["Excesso simulado (%)"].to_numpy(float)/100,
                       m["Ruptura simulada (%)"].to_numpy(float)/100,
                       plano, res["ltm"], close)

def tabela(linhas):
    return pd.DataFrame([{
        "Risco": l["tipo"].capitalize(),
        "Situação": CORES[l["cor"]]["rotulo"], "Nível": l["nivel"],
        "Meses com sinal": l["meses_sinal"] or "—",
        "Maior chance": f"{l['chance_max']:.0%}" if np.isfinite(l["chance_max"]) else "—",
        "Prazo primeiro lote útil": _lab(l["prazo"]) if l["prazo"] is not None else "—",
        "O que fazer": l["acao"], "Por quê": l["porque"],
    } for l in linhas])
