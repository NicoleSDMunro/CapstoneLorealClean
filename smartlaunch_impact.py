"""Métricas de impacto operacional por alteração de lotes Smart Launch.

A comparação usa a MESMA sacola de trajetórias de demanda nas alternativas.
Não estima benefício financeiro nem decisões realmente implementadas.
"""
import numpy as np
import pandas as pd

from smartlaunch_core import balance, LIM

OPTIONS = (
    ("Manter plano", 1.0),
    ("Reduzir 5%", .95),
    ("Reduzir 10%", .90),
    ("Reduzir 15%", .85),
    ("Reduzir 25%", .75),
    ("Reduzir 50%", .50),
    ("Cancelar lote", 0.),
    ("Aumentar 10%", 1.10),
    ("Aumentar 25%", 1.25),
)


def editable_lots(res, close):
    """Somente lotes positivos cujo mês limite (lead time) ainda não passou."""
    return [
        {
            "index": i,
            "month": month,
            "deadline": month - int(res["ltm"]),
            "units": float(res["production"][i]),
        }
        for i,month in enumerate(res["months"])
        if np.isfinite(res["production"][i])
        and float(res["production"][i]) > 0
        and month - int(res["ltm"]) > close
    ]


def consumption_after_target(demand, target_index, months=6):
    """Demanda cumulativa 6 meses após alvo, consistente com forward cover.

    Não extrapola a partir de demanda real: são cenários simulados.
    Caso horizonte termine antes de completar 6 meses, repete o último mês
    simulado, seguindo a hipótese de cauda usada no motor de cobertura.
    """
    demand = np.asarray(demand, dtype=float)
    if demand.ndim != 2 or demand.shape[1] == 0:
        raise ValueError("Demanda simulada deve ter formato cenários × meses.")
    if not 0 <= target_index < demand.shape[1]:
        raise ValueError("Mês-alvo fora do horizonte.")
    available = demand[:,target_index+1:target_index+1+months]
    omitted = months - available.shape[1]
    if omitted:
        tail = np.repeat(demand[:,-1:], omitted, axis=1)
        available = np.concatenate((available,tail),axis=1)
    return available.sum(axis=1), int(omitted)


def outcome_metrics(res, plan, target_index):
    """Mede estoque excedente, vendas perdidas e fill rate em unidades.

    Excesso-alvo = max(0, estoque ao final do alvo - consumo dos 6 meses
    seguintes). São unidades excedentes EXPECTATIVAS, não lucro/caixa salvo.
    Probabilidades e serviço agregados dentro da janela crítica do TCC.
    """
    demand=np.asarray(res["dm"],dtype=float)
    production=np.asarray(plan,dtype=float)
    if demand.ndim != 2 or len(production)!=demand.shape[1]:
        raise ValueError("Plano e cenários não compartilham o mesmo horizonte.")
    if not np.isfinite(production).all() or (production<0).any():
        raise ValueError("O plano precisa conter quantidades finitas e não negativas.")
    stock,lost,cover=balance(res["e0"],production,demand)
    future_consumption,extrapolated=consumption_after_target(demand,target_index)
    excess_target = np.maximum(stock[:,target_index]-future_consumption,0)
    active=np.asarray(res["active"],dtype=bool)
    if not active.any():
        raise ValueError("A janela crítica não contém meses avaliáveis.")
    total_demand=float(demand[:,active].sum())
    total_lost=float(lost[:,active].sum())
    fill_rate=(100*(1-total_lost/total_demand)) if total_demand>0 else 100.0
    return {
        "expected_excess_units": float(excess_target.mean()),
        "expected_lost_units": float(lost[:,active].sum(axis=1).mean()),
        "fill_rate_pct": float(max(0.,min(100.,fill_rate))),
        "risk_excess_target_pct": float((cover[:,target_index]>=LIM).mean()*100),
        "risk_rupture_target_pct": float((lost[:,target_index]>0).mean()*100),
        "risk_excess_window_pct": float((cover[:,active]>=LIM).any(axis=1).mean()*100),
        "risk_rupture_window_pct": float((lost[:,active]>0).any(axis=1).mean()*100),
        "extrapolated_months": extrapolated,
        "target_month": res["months"][target_index],
        "demand_scenarios": len(demand),
        "evaluated_months": int(active.sum()),
    }


def evaluate_lot_options(res, lot_index, target_index):
    """Retorna (tabela de planos, métricas baseline); sem mudar res em memória."""
    if lot_index not in range(len(res["production"])):
        raise ValueError("Lote inexistente.")
    baseline_plan=np.asarray(res["production"],dtype=float)
    initial=float(baseline_plan[lot_index])
    if initial<=0:
        raise ValueError("É necessário um lote positivo para alterar.")
    baseline=outcome_metrics(res,baseline_plan,target_index)
    records=[]
    for name,factor in OPTIONS:
        plan=baseline_plan.copy()
        plan[lot_index]=round(initial*factor)
        values=outcome_metrics(res,plan,target_index)
        records.append({
            "Alternativa": name,
            "Quantidade do lote (un.)": float(plan[lot_index]),
            "Variação do lote (un.)": float(plan[lot_index]-initial),
            "Excesso esperado no mês-alvo (un.)": values["expected_excess_units"],
            "Excesso potencialmente evitado (un.)": (
                baseline["expected_excess_units"]-values["expected_excess_units"]
            ),
            "Vendas perdidas esperadas na janela (un.)": values["expected_lost_units"],
            "Vendas perdidas adicionais (un.)": (
                values["expected_lost_units"]-baseline["expected_lost_units"]
            ),
            "Fill rate simulado (%)": values["fill_rate_pct"],
            "Risco excesso no mês-alvo (%)": values["risk_excess_target_pct"],
            "Risco ruptura no mês-alvo (%)": values["risk_rupture_target_pct"],
            "Risco excesso na janela (%)": values["risk_excess_window_pct"],
            "Risco ruptura na janela (%)": values["risk_rupture_window_pct"],
            "Meses extrapolados após alvo": values["extrapolated_months"],
        })
    frame=pd.DataFrame(records)
    # Alternativa não-dominada se nenhum outro plano tiver menos excesso E
    # menos vendas perdidas esperadas, com melhora estrita em pelo menos um.
    excess=frame["Excesso esperado no mês-alvo (un.)"].to_numpy(dtype=float)
    lost=frame["Vendas perdidas esperadas na janela (un.)"].to_numpy(dtype=float)
    pareto=[]
    for i in range(len(frame)):
        dominated=False
        for j in range(len(frame)):
            if j==i:continue
            if (excess[j]<=excess[i]+1e-6 and lost[j]<=lost[i]+1e-6 and
                (excess[j]<excess[i]-1e-6 or lost[j]<lost[i]-1e-6)):
                dominated=True
                break
        pareto.append(not dominated)
    frame["Não dominada (excesso × perda)"]=pareto
    return frame,baseline


def historical_mape_vs_official(detail, model):
    """Comparação estatística de mesma origem/alvo, NÃO impacto operacional."""
    if detail.empty:
        return None
    def summarize(name):
        sub=detail[detail["Modelo"]==name]
        if sub.empty:return None
        return sub[["Origem","Alvo","APE"]].rename(columns={"APE":name})
    if model=="Oficial":
        group=summarize("Oficial")
        if group is None:return None
        return {"modelo":"Oficial","mape_operacional":float(group["Oficial"].mean()),
                "mape_oficial":float(group["Oficial"].mean()),"pares":len(group),
                "delta_pp":0.}
    o=summarize("Oficial")
    m=summarize(model)
    if o is None or m is None:
        return None
    pairs=m.merge(o,on=["Origem","Alvo"],how="inner")
    if pairs.empty:return None
    mean_official=float(pairs["Oficial"].mean())
    mean_model=float(pairs[model].mean())
    return {
        "modelo":model,"mape_operacional":mean_model,
        "mape_oficial":mean_official,"pares":len(pairs),
        "delta_pp":mean_official-mean_model,
    }
