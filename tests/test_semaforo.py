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
