"""Avaliação mensal experimental de modelos, sem dados empresariais persistidos."""
import numpy as np
import pandas as pd

CANDIDATES=("MEA-P","MEA","Oficial","Naive")

def evaluate_models(product, close, blocks, forecast_fn, known_fn):
    """Backtest rolling h1..h3 sem usar alvos posteriores ao fechamento.
    Todos os concorrentes são avaliados nos MESMOS pares origem/alvo.
    Esta é uma implementação complementar; homologar contra o notebook final.
    """
    pv=blocks[{"P1":"PRODUTO 1","P2":"PRODUTO 2","P3":"PRODUTO 3"}[product]]["PV"]
    actual=known_fn(pv,close)
    if actual.empty:
        return pd.DataFrame(), pd.DataFrame(), None
    start=actual.index.min()
    observations={}
    for origin in sorted(pv.index):
        if origin < start or origin >= close:
            continue
        if not (actual.index<=origin).any():
            continue
        targets=[origin+h for h in (1,2,3) if origin+h in actual.index]
        if not targets:
            continue
        for model in CANDIDATES:
            try:
                pred=forecast_fn(product,targets,origin,blocks,model=model)
            except (ValueError,KeyError,IndexError,TypeError):
                continue
            for target,value in zip(targets,pred):
                if np.isfinite(value) and np.isfinite(actual[target]) and actual[target]>0:
                    observations[(origin,target,model)]=float(value)
    if not observations:
        return pd.DataFrame(),pd.DataFrame(),None
    pairs=set((o,t) for o,t,m in observations)
    common=[(o,t) for o,t in sorted(pairs) if all((o,t,m) in observations for m in CANDIDATES)]
    records=[]
    for origin,target in common:
        for model in CANDIDATES:
            actual_value=float(actual[target])
            predicted=observations[(origin,target,model)]
            records.append(dict(Origem=str(origin),Alvo=str(target),Horizonte=(target-origin).n,
                                Modelo=model,Real=actual_value,Previsto=predicted,
                                Erro=actual_value-predicted,
                                APE=100*abs(actual_value-predicted)/actual_value))
    detail=pd.DataFrame(records)
    if detail.empty:
        return detail,pd.DataFrame(),None
    rows=[]
    for model,g in detail.groupby("Modelo",sort=False):
        errors=g["Erro"].to_numpy()
        rows.append({"Modelo":model,"MAPE (%)":round(float(g["APE"].mean()),2),
                     "MAE":round(float(np.abs(errors).mean()),1),
                     "RMSE":round(float(np.sqrt(np.mean(errors**2))),1),
                     "Viés (un.)":round(float(errors.mean()),1),
                     "Previsões":len(g),"Fechamentos":g["Origem"].nunique(),
                     "Meses-alvo":g["Alvo"].nunique(),
                     "Elegível":len(g)>=3 and g["Origem"].nunique()>=2})
    ranking=pd.DataFrame(rows).sort_values(["Elegível","MAPE (%)"],ascending=[False,True]).reset_index(drop=True)
    eligible=ranking[ranking["Elegível"]]
    winner=str(eligible.iloc[0]["Modelo"]) if not eligible.empty else None
    return detail,ranking,winner

def monthly_alert_rows(result, limit=180, threshold=.025):
    """Probabilidades por mês e alertas restritos à janela crítica."""
    excess=(result["cov"]>=limit).mean(axis=0)
    shortage=(result["lost"]>0).mean(axis=0)
    rows=[]
    for j,month in enumerate(result["months"]):
        window=bool(result["active"][j])
        rows.append({"Mês":str(month),"Excesso (%)":round(float(excess[j]*100),1),
                     "Ruptura (%)":round(float(shortage[j]*100),1),
                     "Janela crítica":window,
                     "Alerta excesso":bool(window and excess[j]>.025),
                     "Alerta ruptura":bool(window and shortage[j]>.025)})
    return pd.DataFrame(rows)
