"""Métricas de impacto operacional por alteração de lotes Smart Launch.

A comparação usa a MESMA sacola de trajetórias de demanda nas alternativas.
Não estima benefício financeiro nem decisões realmente implementadas.
"""
import numpy as np
import pandas as pd

from smartlaunch_core import balance, LIM, AUMENTO_MAX_RUPTURA
from smartlaunch_supply import future_lots

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
    """Lotes futuros com prazo à frente ou no próprio mês-limite.

    No mês-limite a comparação é somente exploratória; não garante execução.
    """
    return [
        {
            "index": lot["index"], "month": lot["month"],
            "deadline": lot["deadline"], "units": lot["units"],
            "boundary": lot["boundary"], "situation": lot["situation"],
        }
        for lot in future_lots(res, close) if lot["available_for_analysis"]
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



def month_signals(res, plan):
    """Sinais por mês da janela crítica, conforme os gatilhos de percentil do TCC."""
    demand=np.asarray(res["dm"],dtype=float)
    stock,lost,cover=balance(res["e0"],np.asarray(plan,dtype=float),demand)
    active=np.asarray(res["active"],dtype=bool)
    excess=set();rupture=set();p_rup=[]
    for i in np.flatnonzero(active):
        if np.isfinite(cover[:,i]).all() and np.nanpercentile(cover[:,i],97.5)>=LIM:
            excess.add(i)
        if np.percentile(lost[:,i],97.5)>0:
            rupture.add(i)
        p_rup.append(float((lost[:,i]>0).mean()))
    return excess,rupture,np.array(p_rup)


def tcc_check(res, plan, base_signals=None):
    """Compara sinais de um lote com o plano original, sem afirmar executabilidade."""
    exc0,rup0,p0=base_signals if base_signals is not None else month_signals(res,res["production"])
    exc,rup,p=month_signals(res,plan)
    rise=float(np.max(p-p0)) if len(p) else 0.
    return {"new_excess":bool(exc-exc0),
            "new_rupture":bool(rup-rup0),
            "max_rupture_rise":rise}


def tcc_lot_limits(res, lot_index, step=5):
    """Maior corte e aumento sequencial em passos de 5%, pelo critério do ZIP.

    Para no primeiro passo que viola a regra; isso não é otimização global.
    """
    plan0=np.asarray(res["production"],dtype=float)
    q=float(plan0[lot_index])
    if q<=0:
        raise ValueError("O lote precisa ter quantidade positiva.")
    if step<=0 or 100%step:
        raise ValueError("O passo precisa dividir 100.")
    base=month_signals(res,plan0)
    cut=0
    for pct in range(step,101,step):
        plan=plan0.copy();plan[lot_index]=q*(1-pct/100)
        chk=tcc_check(res,plan,base)
        if chk["new_rupture"] or chk["max_rupture_rise"]>AUMENTO_MAX_RUPTURA:
            break
        cut=pct
    increase=0
    for pct in range(step,101,step):
        plan=plan0.copy();plan[lot_index]=q*(1+pct/100)
        if tcc_check(res,plan,base)["new_excess"]:
            break
        increase=pct
    return {"max_cut_pct":cut,"max_cut_units":q*cut/100,
            "max_increase_pct":increase,"step":step}


def evaluate_lot_options(res, lot_index, target_index):
    """Retorna (tabela de planos, métricas baseline); sem mudar res em memória."""
    if lot_index not in range(len(res["production"])):
        raise ValueError("Lote inexistente.")
    baseline_plan=np.asarray(res["production"],dtype=float)
    initial=float(baseline_plan[lot_index])
    if initial<=0:
        raise ValueError("É necessário um lote positivo para alterar.")
    baseline=outcome_metrics(res,baseline_plan,target_index)
    base_signals=month_signals(res,baseline_plan)
    records=[]
    for name,factor in OPTIONS:
        plan=baseline_plan.copy()
        plan[lot_index]=round(initial*factor)
        values=outcome_metrics(res,plan,target_index)
        chk=tcc_check(res,plan,base_signals)
        if factor<1:
            ok=not chk["new_rupture"] and chk["max_rupture_rise"]<=AUMENTO_MAX_RUPTURA
        elif factor>1:
            ok=not chk["new_excess"]
        else:
            ok=True
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
            "Cria sinal novo de ruptura": chk["new_rupture"],
            "Cria sinal novo de excesso": chk["new_excess"],
            "Maior aumento da chance de ruptura num mês (p.p.)":
                round(100*chk["max_rupture_rise"],1),
            "Dentro do critério do TCC": ok,
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


def simulate_monthly_scenario(res, alternative_plan, *, coverage_days=180,
                              uncertainty_multiplier=1.0):
    """Compara produção original vs. edição de vários lotes, na mesma sacola.

    O simulador mensal é inspirado no Excel SmartLaunch_simulador_jun-26.
    Nenhuma previsão/modelo é recalculado aqui: o motor da análise confirmada
    fornece as 1.000 trajetórias. Premissas editáveis aplicam-se simetricamente
    aos dois planos. Não altera res em memória nem executa pedidos reais.
    """
    original=np.asarray(res["production"],dtype=float)
    candidate=np.asarray(alternative_plan,dtype=float)
    central=np.asarray(res["center"],dtype=float)
    simulated=np.asarray(res["dm"],dtype=float)
    if original.shape!=candidate.shape or candidate.ndim!=1:
        raise ValueError("Lotes editados e plano original devem ter os mesmos meses.")
    if not np.isfinite(candidate).all() or np.any(candidate < 0):
        raise ValueError("A produção simulada deve ser finita e não negativa.")
    if not 30 <= float(coverage_days) <= 360:
        raise ValueError("A cobertura de sensibilidade deve ficar entre 30 e 360 dias.")
    if not 0.5 <= float(uncertainty_multiplier) <= 2.0:
        raise ValueError("O multiplicador de incerteza deve ficar entre 0,5 e 2,0.")
    if simulated.ndim!=2 or simulated.shape[1]!=len(original):
        raise ValueError("Trajetórias inválidas: demanda e produção sem horizonte comum.")

    # Multiplicador 1,0 mantém exatamente as trajetórias do motor do TCC.
    # Outros valores são sensibilidade em torno da previsão central.
    if abs(float(uncertainty_multiplier)-1.0) < 1e-12:
        demand=simulated
    else:
        demand=np.maximum(0,central[None,:]+float(uncertainty_multiplier)*
                          (simulated-central[None,:]))
    stock0,lost0,cov0=balance(res["e0"],original,demand)
    stock1,lost1,cov1=balance(res["e0"],candidate,demand)

    months=res["months"]
    H=len(months)
    active=np.asarray(res["active"],dtype=bool)
    evaluated=np.asarray(res.get("evaluated",
                       np.array([j<H-1 for j in range(H)])),dtype=bool)
    eligible=active & evaluated
    if not active.any():
        raise ValueError("Sem meses na janela crítica para comparar.")
    n=len(demand)
    full=int(float(coverage_days)//30)
    fraction=(float(coverage_days)/30)-full
    excess0=np.empty_like(stock0)
    excess1=np.empty_like(stock1)
    for j in range(H):
        # Consumo dos próximos dias de cobertura; repete o último mês
        # simulado na cauda, como hipótese explícita do XLSX e do método.
        required=np.zeros(n)
        for delta in range(1,full+1):
            required+=demand[:,min(j+delta,H-1)]
        if fraction>1e-10:
            required+=fraction*demand[:,min(j+full+1,H-1)]
        excess0[:,j]=np.maximum(0,stock0[:,j]-required)
        excess1[:,j]=np.maximum(0,stock1[:,j]-required)

    ex0=np.where(evaluated,(cov0>=coverage_days).mean(axis=0)*100,np.nan)
    ex1=np.where(evaluated,(cov1>=coverage_days).mean(axis=0)*100,np.nan)
    ru0=(lost0>0).mean(axis=0)*100
    ru1=(lost1>0).mean(axis=0)*100
    monthly=[]
    for j,month in enumerate(months):
        v0=cov0[:,j]
        v1=cov1[:,j]
        v0=v0[np.isfinite(v0)]
        v1=v1[np.isfinite(v1)]
        monthly.append({
            "Mês":str(month),
            "Produção original (un.)":float(original[j]),
            "Produção simulada (un.)":float(candidate[j]),
            "Variação do lote (un.)":float(candidate[j]-original[j]),
            "Demanda média (un.)":float(demand[:,j].mean()),
            "Estoque P50 atual (un.)":float(np.median(stock0[:,j])),
            "Estoque P50 simulado (un.)":float(np.median(stock1[:,j])),
            "Excedente atual (un.)":float(excess0[:,j].mean()),
            "Excedente simulado (un.)":float(excess1[:,j].mean()),
            "Excesso atual (%)":float(ex0[j]) if np.isfinite(ex0[j]) else np.nan,
            "Excesso simulado (%)":float(ex1[j]) if np.isfinite(ex1[j]) else np.nan,
            "Ruptura atual (%)":float(ru0[j]),
            "Ruptura simulada (%)":float(ru1[j]),
            "Cobertura atual P50 (dias)":float(np.median(v0)) if len(v0) and evaluated[j] else np.nan,
            "Cobertura simulada P50 (dias)":float(np.median(v1)) if len(v1) and evaluated[j] else np.nan,
            "Janela crítica":bool(active[j]),
            "Cobertura avaliável":bool(evaluated[j]),
        })
    def aggregate(stock,lost,excess,ex_prob,ru_prob):
        demand_total=float(demand[:,active].sum())
        lost_total=float(lost[:,active].sum())
        fill=(100*(1-lost_total/demand_total)) if demand_total>0 else 100.0
        peak_ex=float(np.max(excess[:,eligible].mean(axis=0))) if eligible.any() else np.nan
        maxrisk=float(np.nanmax(ex_prob[eligible])) if eligible.any() else np.nan
        maxrup=float(np.max(ru_prob[active]))
        return {
            "Excedente no pior mês (un.)":peak_ex,
            "Vendas perdidas na janela (un.)":float(lost[:,active].sum(axis=1).mean()),
            "Vendas atendidas na janela (un.)":float(demand[:,active].sum(axis=1).mean()
                                                   -lost[:,active].sum(axis=1).mean()),
            "Fill rate (%)":max(0.,min(100.,fill)),
            "Maior chance de excesso (%)":maxrisk,
            "Maior chance de ruptura (%)":maxrup,
        }
    before=aggregate(stock0,lost0,excess0,ex0,ru0)
    after=aggregate(stock1,lost1,excess1,ex1,ru1)
    rupture_rise=float(np.max(ru1[active]-ru0[active]))
    new_rupture=bool(np.any((ru1[active]>2.5)&(ru0[active]<=2.5)))
    new_excess=bool(eligible.any() and np.any((ex1[eligible]>2.5)&(ex0[eligible]<=2.5)))
    return {
        "monthly":pd.DataFrame(monthly),"original":before,"simulated":after,
        "demand":demand,"same_demands":True,
        "changed_lots":int(np.count_nonzero(np.abs(candidate-original)>1e-7)),
        "new_rupture_signal":new_rupture,
        "new_excess_signal":new_excess,
        "max_rupture_rise_pp":rupture_rise,
        "evaluated_months":int(eligible.sum()),
        "extrapolates_future_consumption":True,
        "coverage_days":float(coverage_days),
        "uncertainty_multiplier":float(uncertainty_multiplier),
        "delta":{
            key:after[key]-before[key] for key in before
        },
    }
