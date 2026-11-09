"""Smoke test: workbook fictício, nenhum dado da L'Oréal armazenado."""
import ast
import io
from pathlib import Path
import numpy as np
import pandas as pd
import openpyxl
from openpyxl import Workbook

src=Path("smartlaunch_app.py").read_text()
tree=ast.parse(src)
# Carrega somente funções e constantes (não inicia a interface Streamlit).
keep=[]
for node in tree.body:
    if isinstance(node,(ast.Import,ast.ImportFrom)):
        keep.append(node)
    elif isinstance(node,ast.FunctionDef):
        node.decorator_list=[];keep.append(node)
    elif isinstance(node,ast.Assign) and all(isinstance(t,ast.Name) for t in node.targets):
        if node.targets[0].id in {"MONTHS","NAMES","MODEL","ANALOG","SHEETS","SEED","N","LIM"}:keep.append(node)
mod=ast.Module(body=keep,type_ignores=[])
ns={}
exec(compile(ast.fix_missing_locations(mod),"smartlaunch_core","exec"),ns)
load_data=ns["load_data"];forecast=ns["forecast"];simulate=ns["simulate"]
wb=Workbook()
base=wb.active;base.title="Base"
base.append(["PRODUTO","Cobertura Target (dias)","Maior LT de Insumo (in weeks)"])
for k in (1,2,3):
    base.append([k,[70,90,59][k-1],[16,10,8][k-1]])
start=pd.Period("2025-01",freq="M")
months=[start+i for i in range(24)]
revmonths=[start+i for i in range(14)]
def lab(p):return ns["label"](p)
for name in list(ns["SHEETS"].values())+sorted(set(sum(ns["ANALOG"].values(),[]))):
    ws=wb.create_sheet(name)
    offset=18000 if "BENCH" in name else 40000
    for kind in ("PV (SELL IN)","PRODUÇÃO","ESTOQUE"):
        ws.append([kind]);ws.append(["Mes/Ano"]+[lab(m) for m in months]);ws.append(["Mes/Ano"]+["Demanda + Plano DataM" for _ in months])
        for ridx,review in enumerate(revmonths):
            if kind=="PV (SELL IN)":v=[(0 if "BENCH" not in name and i<5 else offset*(1+0.03*i)) for i in range(24)]
            elif kind=="PRODUÇÃO":v=[50000 for i in range(24)]
            else:v=[85000 for i in range(24)]
            ws.append([lab(review)]+v)
buf=io.BytesIO();wb.save(buf)
base,blocks=load_data(buf.getvalue())
assert len(blocks)==8,(len(blocks),blocks.keys())
for name in ns["SHEETS"].values():
    assert all(len(blocks[name][k].index)>0 for k in ("PV","PROD","EST")),name
for product in ("P1","P2","P3"):
    origin=pd.Period("2025-10",freq="M")
    fc=forecast(product,[origin+1,origin+2,origin+3],origin,blocks)
    assert len(fc)==3 and np.isfinite(fc).all(),(product,fc)
    res=simulate(product,origin,blocks,base)
    assert res["dm"].shape[0]==1000
    assert np.isfinite(res["cov"]).all()
    assert (res["stock"]>=0).all()
    print(product,"forecast",fc.tolist(),"error bag",len(res["errors"]))
print("SMOKE PASS")
