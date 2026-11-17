"""Testes do semáforo — excesso é foco, ruptura é restrição complementar."""
import numpy as np
import pandas as pd
from smartlaunch_semaforo import classificar, cor_do_produto, lotes_alteraveis

close = pd.Period("2026-06",freq="M")
months = [close+k for k in range(1,7)]
active = np.array([1,1,1,1,1,0],bool)
eval_ = active.copy()
zero=np.zeros(6)

def linha(tipo,p_exc,p_rup,prod,ltm=2):
    return {l["tipo"]:l for l in classificar(months,active,eval_,p_exc,p_rup,prod,ltm,close)}[tipo]

assert linha("excesso",[.5,.4,.3,.2,.1,np.nan],zero,zero)["cor"]=="vermelho"
assert "comercial" in linha("excesso",[.5,.4,.3,.2,.1,np.nan],zero,zero)["acao"]
prod=np.array([0,0,100,100,100,0.])
assert linha("excesso",[0,0,.05,.1,.25,np.nan],zero,prod)["cor"]=="vermelho"
prod=np.array([0,0,0,100,100,0.])
assert linha("excesso",[0,0,.01,.1,.25,np.nan],zero,prod)["cor"]=="amarelo"
assert linha("excesso",[0,0,.05,.1,.15,np.nan],zero,prod)["cor"]=="verde"
assert linha("ruptura",zero,zero,prod)["cor"]=="cinza"
l=linha("ruptura",zero,[0,.23,0,0,0,0],np.array([0,0,100,100,100,0.]))
assert l["cor"]=="vermelho" and "alocação" in l["acao"]
assert cor_do_produto(classificar(months,active,eval_,zero,zero,prod,2,close))=="cinza"
assert len(lotes_alteraveis(months,prod,2,close))==2
print("PASS: aviso, alerta, cor, prazo e disponibilidade teórica.")

from smartlaunch_semaforo import cor_por_mes, vies_persistente

l=linha("excesso", [.5,.4,.3,.2,.1,np.nan], zero, zero)
assert l["decisor"].startswith("Comercial")
assert "jul/26" in l["ate"]
l=linha("excesso", [0,0,.05,.1,.25,np.nan], zero, np.array([0,0,100,100,100,0.]))
assert l["decisor"].startswith("Supply")
assert l["ate"].startswith("jul/26")
cores=cor_por_mes(months, active, eval_, [0,0,.05,.1,.25,np.nan], zero,
                  np.array([0,0,100,100,100,0.]), 2, close)
assert [x["excesso"][0] for x in cores] == [
    "cinza","cinza","verde","verde","vermelho","fora"
]
assert vies_persistente([-1]*8)["cor"]=="amarelo"
assert vies_persistente([-1]*7+[1])["cor"]=="verde"
assert vies_persistente([-1,1,-1])["cor"]=="cinza"
print("PASS: responsáveis, prazos, cores mensais e viés exploratório.")
