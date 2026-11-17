"""Evolução dos semáforos: reconstruções históricas por fechamento e mês-alvo.

Os alertas são reconstituídos com informações da origem de cada revisão.
As etiquetas de excesso observado dependem da cobertura reestimada com
vendas posteriores disponíveis e possível extensão da última demanda; são
uma comparação retrospectiva, não uma validação prospectiva independente.
"""
import numpy as np
import pandas as pd

from smartlaunch_core import SHEETS, known, simulate, coverage, LIM
from smartlaunch_semaforo import cor_por_mes

CODIGO = {"fora": 0, "cinza": 1, "verde": 2, "amarelo": 3, "vermelho": 4}


def cobertura_observada(p, fechamento, blocks):
    b = blocks[SHEETS[p]]
    vendido = known(b["PV"], fechamento)
    if vendido.empty:
        return {}
    meses = list(vendido.index)
    saldos = []
    for mes in meses:
        revisao = mes + 1
        valor = (b["EST"].loc[revisao, mes]
                 if revisao in b["EST"].index and mes in b["EST"].columns
                 else np.nan)
        saldos.append(float(valor) if pd.notna(valor) else np.nan)
    saldos = np.asarray(saldos, dtype=float)
    # Meses sem dados posteriores não são declarados cobertos.
    if len(meses) < 2:
        return {}
    cob = coverage(np.nan_to_num(saldos, nan=0.0)[None, :],
                   vendido.to_numpy(float)[None, :])[0]
    return {m: float(cob[i]) for i, m in enumerate(meses)
            if i < len(meses)-1 and np.isfinite(saldos[i]) and np.isfinite(cob[i])}


def linha_do_tempo(p, close, blocks, base, model=None):
    vendido = known(blocks[SHEETS[p]]["PV"], close)
    if vendido.empty:
        return pd.DataFrame(), []
    inicio = vendido.index.min()
    real = cobertura_observada(p, close, blocks)
    linhas = []
    sem_simulacao = []
    for origem in pd.period_range(inicio-1, close, freq="M"):
        try:
            res = simulate(p, origem, blocks, base, operational_model=model)
        except (ValueError, KeyError, IndexError, TypeError) as e:
            sem_simulacao.append((origem, str(e)))
            continue
        validos = np.asarray(res["evaluated"], bool)
        p_exc = np.where(validos, (res["cov"] >= LIM).mean(axis=0), np.nan)
        p_rup = (res["lost"] > 0).mean(axis=0)
        for m in cor_por_mes(res["months"], res["active"], validos, p_exc,
                             p_rup, res["production"], res["ltm"], origem):
            if not m["na_janela"]:
                continue
            mes = m["mes"]
            rc = real.get(mes, np.nan)
            linhas.append({
                "fechamento": origem, "mes": mes,
                "cor_excesso": m["excesso"][0],
                "chance_excesso": m["excesso"][1],
                "cor_ruptura": m["ruptura"][0],
                "chance_ruptura": m["ruptura"][1],
                "excesso_real": (float(rc) >= LIM) if np.isfinite(rc) else None,
            })
    return pd.DataFrame(linhas), sem_simulacao
