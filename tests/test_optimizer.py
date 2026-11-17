"""Provas sintéticas: busca multi-lote usa 1.000 demandas pareadas, não promete ótimo."""
import numpy as np
import pandas as pd

from smartlaunch_optimizer import search_supply_combinations
from smartlaunch_impact import simulate_monthly_scenario

rng=np.random.default_rng(42)
months=list(pd.period_range("2026-07",periods=6,freq="M"))
center=np.full(6,100.)
demand=np.maximum(0,center+rng.normal(0,8,(1000,6)))
res={
    "months":months,
    "production":np.array([300.,300.,300.,300.,300.,0.]),
    "e0":150.,
    "dm":demand,
    "center":center,
    "active":np.array([True,True,True,True,True,False]),
    "evaluated":np.array([True,True,True,True,True,False]),
    "ltm":1,"window":5
}
close=pd.Period("2026-06",freq="M")
r=search_supply_combinations(res,close,budget=2500,max_cut_pct=50,
                             fill_drop_limit_pp=0.2,top_k=6)
assert r["candidates_checked"]>500,(r["candidates_checked"],r["reason"])
assert r["grid_size"]>=r["candidates_checked"]
assert len(r["eligible_lots"])>=2,r["reason"]
assert r["best"] is not None,r["reason"]
assert r["best"]["Excedente evitado no pior mês (un.)"]>0
assert len(r["shortlist"])<=6
assert "C1" in r["plans"]
assert all(float(x)>=0 for x in r["plans"]["C1"])
assert np.allclose(res["production"],[300,300,300,300,300,0])
assert r["plans"]["C1"][-1]==0.0,"Lote além da janela avaliável não deve ser modificado"
verify=simulate_monthly_scenario(res,r["plans"]["C1"])
assert abs(verify["delta"]["Excedente no pior mês (un.)"]+
           r["best"]["Excedente evitado no pior mês (un.)"])<1e-5
assert verify["max_rupture_rise_pp"]<=2.5+1e-8
assert not verify["new_rupture_signal"]
assert not verify["new_excess_signal"]

# Reprodutibilidade dentro do mesmo fechamento e mesmas premissas.
r2=search_supply_combinations(res,close,budget=2500,max_cut_pct=50,
                              fill_drop_limit_pp=0.2,top_k=6)
assert r2["best"]==r["best"]
assert np.allclose(r2["plans"]["C1"],r["plans"]["C1"])

# Sensibilidade em ambos os planos, sem misturar uma sacola de demandas diferente.
custom=search_supply_combinations(res,close,budget=1000,max_cut_pct=25,
                coverage_days=150,uncertainty_multiplier=1.25,
                fill_drop_limit_pp=0.3)
assert custom["candidates_checked"]>0
if custom["best"]:
    valid=simulate_monthly_scenario(res,custom["plans"]["C1"],
              coverage_days=150,uncertainty_multiplier=1.25)
    assert not valid["new_rupture_signal"]
    assert valid["max_rupture_rise_pp"]<=2.5+1e-8

# Se nenhum lote altera o estoque da janela avaliada, não fabricar solução.
none={**res,"production":np.zeros(6)}
no=search_supply_combinations(none,close,budget=1000)
assert no["candidates_checked"]==0 and no["best"] is None

# Espaço de busca contém cortes, aumentos e remanejamentos mistos.
from smartlaunch_optimizer import _candidate_grid
mix,space=_candidate_grid([{"index":1},{"index":2}],20,10,1000,42)
assert space==len(mix)
assert np.any(mix<0) and np.any(mix>0)
assert any(a<0 and b>0 for a,b in mix)
assert any(a==0 and b==0 for a,b in mix)

try:
    search_supply_combinations(res,close,budget=17)
    assert False,"Orçamento inválido deveria falhar"
except ValueError:
    pass
print("OPTIMIZER PASS: múltiplos lotes, proteção de serviço, repetição e restrições")
