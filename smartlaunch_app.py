"""Smart Launch — painel operacional. Dados carregados somente na sessão (sem salvar arquivos)."""
import io
import math
import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import openpyxl

st.set_page_config(page_title="Smart Launch | L'Oréal", page_icon="📦", layout="wide")
st.markdown("""<style>
.stApp{background:#090909;color:#f3f3f3}
[data-testid="stMetric"]{background:#171717;border:1px solid #303030;padding:14px;border-radius:10px}
h1,h2,h3{letter-spacing:-.03em}
div[data-testid="stAlert"]{border-radius:8px}
</style>""",unsafe_allow_html=True)

MONTHS={"jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,"jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12}
NAMES={v:k for k,v in MONTHS.items()}
MODEL={"P1":"MEA-P","P2":"MEA","P3":"Oficial"}
ANALOG={"P1":["BENCH A_1","BENCH B_1"],"P2":["BENCH C_2"],"P3":["BENCH D_3","BENCH E_3"]}
SHEETS={"P1":"PRODUTO 1","P2":"PRODUTO 2","P3":"PRODUTO 3"}
SEED=20261021
N=1000
LIM=180

def period(v):
    if isinstance(v,pd.Period): return v
    if isinstance(v,pd.Timestamp): return v.to_period("M")
    s=str(v).strip().lower()
    m=re.match(r"^(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s*[/ -]\s*(20\d{2}|\d{2})$",s)
    if not m:return None
    y=int(m.group(2))
    return pd.Period(year=2000+y if y<100 else y,month=MONTHS[m.group(1)],freq="M")

def label(p):
    return f"{NAMES[p.month]}/{str(p.year)[-2:]}"

def parse_blocks(ws):
    """Layout original: títulos PV / PRODUÇÃO / ESTOQUE e linha Mes/Ano antes de cada triângulo."""
    blocks={}; kind=None; header={}
    for row in ws.iter_rows(values_only=True):
        first=row[0] if row else None
        p=period(first)
        if isinstance(first,str) and p is None:
            s=first.strip().upper()
            if "ESTOQUE" in s:kind="EST"
            elif "PRODU" in s:kind="PROD"
            elif s.startswith("PV"):kind="PV"
            if kind and ("ESTOQUE" in s or "PRODU" in s or s.startswith("PV")):
                blocks.setdefault(kind,{})
            if s=="MES/ANO":
                parsed={j:period(x) for j,x in enumerate(row) if period(x) is not None}
                # A linha seguinte também se chama Mes/Ano, mas traz descrições.
                # Não apagar os meses do cabeçalho válido.
                if parsed: header=parsed
            continue
        if p is not None and kind and header:
            blocks[kind][p]={m:float(row[j] or 0) for j,m in header.items() if j<len(row) and isinstance(row[j],(int,float))}
    return {key:pd.DataFrame.from_dict(v,orient="index").sort_index() for key,v in blocks.items()}

def read_base(wb):
    if "Base" not in wb.sheetnames:raise ValueError('Arquivo incompatível: falta a aba "Base". Envie o Triangulo_Produtos_V2.xlsx da metodologia final, não a base antiga A–P.')
    rows=list(wb["Base"].values)
    for row in rows:
        cells=[str(x).strip().lower() if x is not None else "" for x in row]
        if "produto" in cells and any("cobertura" in x for x in cells):
            ip=cells.index("produto")
            ic=next(i for i,x in enumerate(cells) if "cobertura" in x)
            il=next((i for i,x in enumerate(cells) if "lt" in x),None)
            if il is None:continue
            result={}
            for r in rows[rows.index(row)+1:]:
                raw=str(r[ip]).strip() if ip<len(r) else ""
                key="P"+raw.replace("P","").replace(".0","")
                if key in MODEL and isinstance(r[ic],(float,int)) and isinstance(r[il],(float,int)):
                    result[key]=(float(r[ic]),float(r[il]))
            if result:return result
    raise ValueError("Não foi possível encontrar LT e cobertura por produto na aba Base.")

@st.cache_data(show_spinner=False)
def load_data(content):
    wb=openpyxl.load_workbook(io.BytesIO(content),read_only=True,data_only=True)
    missing=[s for s in list(SHEETS.values())+sorted(set(sum(ANALOG.values(),[]))) if s not in wb.sheetnames]
    if missing:raise ValueError("A planilha não é o Triangulo_Produtos_V2.xlsx do TCC final. Abas ausentes: "+", ".join(missing)+". Não use a Base de Dados - PUC (2).xlsx antiga (A–P).")
    base=read_base(wb)
    missingbase=[p for p in MODEL if p not in base]
    if missingbase:raise ValueError("Sem LT/cobertura na aba Base: "+", ".join(missingbase))
    blocks={s:parse_blocks(wb[s]) for s in list(SHEETS.values())+sorted(set(sum(ANALOG.values(),[])))}
    for p,s in SHEETS.items():
        if any(k not in blocks[s] for k in ("PV","PROD","EST")):
            raise ValueError(f"{s}: são necessários os blocos PV, PRODUÇÃO e ESTOQUE.")
    wb.close()
    return base,blocks

def known(pv,c):
    """Realizado m = valor da coluna m na revisão m+1 (conhecido no fechamento c)."""
    vals={}
    for m in pv.columns:
        if m<=c and m+1 in pv.index:
            x=pv.loc[m+1,m]
            if pd.notna(x):vals[m]=float(x)
    s=pd.Series(vals,dtype=float).sort_index()
    suspect=pd.Period("2025-09",freq="M")
    if suspect in s and s[suspect]==0 and suspect-1 in s and suspect+1 in s:
        s[suspect]=(s[suspect-1]+s[suspect+1])/2
    pos=s[s>0]
    return s[s.index>=pos.index[0]] if not pos.empty else pd.Series(dtype=float)

def analog_series(blocks,c):
    return {b:known(blocks[b]["PV"],c) for b in set(sum(ANALOG.values(),[]))}

def pipe_index(blocks,c):
    ix=[]
    for b,s in analog_series(blocks,c).items():
        a=np.log10(s.to_numpy(float)) if len(s) and (s>0).all() else np.array([])
        if len(a)>=6:ix.append(a[:3]-a[3:].mean())
    if not ix:raise ValueError("São necessários benchmarks com pelo menos 6 vendas conhecidas para estimar o pipe.")
    return np.mean(ix,axis=0)

def forecast(p,months,c,blocks,model=None):
    model=model or MODEL[p]
    sheet=SHEETS[p]; own=known(blocks[sheet]["PV"],c)
    historical=known(blocks[sheet]["PV"],max(blocks[sheet]["PV"].index))
    start=historical.index.min() if not historical.empty else None
    if start is None or pd.isna(start):raise ValueError(f"{p}: sem venda realizada.")
    if model=="Oficial":
        pv=blocks[sheet]["PV"]
        v=c+1
        if v not in pv.index:raise ValueError(f"Não existe revisão {label(v)} para {p}.")
        return np.array([float(pv.loc[v,m]) if m in pv.columns and pd.notna(pv.loc[v,m]) else np.nan for m in months])
    benches=ANALOG[p]
    if model=="MEA-P":indexes=pipe_index(blocks,c)
    else:indexes=np.zeros(3)
    ys=np.log10(own.to_numpy(float)) if len(own) and (own>0).all() else np.array([])
    ys=ys.copy()
    ys[:min(3,len(ys))]-=indexes[:min(3,len(ys))]
    levels=[]
    cutoff=min(c,start-1)
    for b in benches:
        s=known(blocks[b]["PV"],cutoff)
        if len(s)==0 or (s<=0).any():continue
        bs=np.log10(s.to_numpy(float))
        bs[:min(3,len(bs))]-=indexes[:min(3,len(bs))]
        levels.append(np.concatenate([bs,ys]).mean())
    if not levels:raise ValueError(f"{p}: benchmark insuficiente para {model}.")
    level=np.mean(levels)
    return np.array([10**(level+(indexes[(m-start).n] if 0<=(m-start).n<3 else 0)) for m in months])

def history_errors(p,c,blocks):
    """Backtest mensal h=1..3 somente com alvos realizados e origens passadas.
    Sacola de arranque (origens com 3 a 5 meses conhecidos), como no piloto."""
    pv=blocks[SHEETS[p]]["PV"]
    last=known(pv,c)
    if last.empty:return np.array([]),0
    start=last.index.min()
    rows=[]
    for n in (3,4,5):
        origin=start+n-1
        if origin>=c:continue
        months=[origin+h for h in (1,2,3)]
        try:fc=forecast(p,months,origin,blocks)
        except (ValueError,KeyError):continue
        for m,f in zip(months,fc):
            if m in last.index and np.isfinite(f):
                rows.append(float(last.loc[m])-float(f))
    return np.asarray(rows,dtype=float),len(rows)

def coverage(e,dm):
    """Forward cover, 30 dias/mês; extrapolação após último mês pela última demanda."""
    out=np.zeros_like(e)
    n,h=e.shape
    for j in range(h):
        stock=e[:,j].copy()
        days=np.zeros(n)
        active=stock>0
        future=np.concatenate([dm[:,j+1:],np.maximum(dm[:,-1:],1e-9)],axis=1)
        for k in range(future.shape[1]):
            d=np.maximum(future[:,k],1e-9)
            partial=active & (stock<=d)
            days[partial]+=30*stock[partial]/d[partial]
            active[partial]=False
            days[active]+=30
            stock[active]-=d[active]
        if active.any():
            days[active]+=30*stock[active]/np.maximum(dm[active,-1],1e-9)
        out[:,j]=days
    return out

def balance(e0,plan,dm):
    n,h=dm.shape
    stock=np.empty_like(dm);lost=np.empty_like(dm)
    e=np.full(n,float(e0))
    for j in range(h):
        avail=np.maximum(e+plan[j],0)
        lost[:,j]=np.maximum(dm[:,j]-avail,0)
        e=np.maximum(avail-dm[:,j],0)
        stock[:,j]=e
    return stock,lost,coverage(stock,dm)

def simulate(p,c,blocks,base,method="Normal (0, s)",persistent=False):
    sheet=SHEETS[p]
    b=blocks[sheet]
    review=c+1
    pv=b["PV"]
    months=[m for m in sorted(pv.columns) if m>c and m in b["PROD"].columns]
    if review not in b["PROD"].index or review not in b["EST"].index:
        raise ValueError(f"Sem produção/estoque na revisão {label(review)}.")
    if c not in b["EST"].columns:raise ValueError("Sem estoque inicial no fechamento.")
    if not months:raise ValueError("Não existem meses futuros nesta revisão.")
    production=np.array([float(b["PROD"].loc[review,m]) for m in months])
    e0=float(b["EST"].loc[review,c])
    center=forecast(p,months,c,blocks)
    if not np.isfinite(center).all():raise ValueError("Faltam previsões centrais na revisão.")
    errors,num=history_errors(p,c,blocks)
    if num<2:raise ValueError(f"Apenas {num} erros de arranque conhecidos. Simulação indisponível (mínimo 2).")
    sd=float(np.std(errors,ddof=1))
    rng=np.random.default_rng(SEED+int(p[1:])*1000+c.ordinal)
    if method=="Normal (0, s)":
        eps=rng.normal(0,sd,(N,1 if persistent else len(months)))
    else:
        eps=rng.choice(errors,size=(N,1 if persistent else len(months)),replace=True)-errors.mean()
    if persistent:eps=np.repeat(eps,len(months),axis=1)
    dm=np.maximum(center+eps,0)
    stock,lost,cov=balance(e0,production,dm)
    days,lt=base[p];ltm=math.ceil(lt*7/30);window=ltm+math.ceil(days/30)+1
    active=np.array([j<window for j in range(len(months))])
    return dict(months=months,production=production,e0=e0,center=center,errors=errors,sd=sd,dm=dm,stock=stock,lost=lost,cov=cov,active=active,ltm=ltm,window=window)

def impacts(res,p,new_plan,baseline):
    s,l,c=balance(res["e0"],new_plan,res["dm"])
    win=res["active"]
    return dict(excesso=float((c[:,win]>=LIM).any(axis=1).mean()),ruptura=float((l[:,win]>0).any(axis=1).mean()),
                delta_excesso=float((c[:,win]>=LIM).any(axis=1).mean()-baseline["excesso"]),
                delta_ruptura=float((l[:,win]>0).any(axis=1).mean()-baseline["ruptura"]))

def fmt(n):return f"{n:,.0f}".replace(",",".")

st.title("SMART LAUNCH")
st.caption("L'Oréal | Apoio à decisão de Supply Chain em lançamentos · Metodologia final do TCC")
file=st.file_uploader("Carregue o Triangulo_Produtos_V2.xlsx da L'Oréal (os dados permanecem nesta sessão)",type=["xlsx"])
if file is None:
    st.info("Envie a planilha original com as abas PRODUTO 1–3, benchmarks e Base. O painel não utiliza dados demonstrativos inventados.")
    st.stop()
try:base,blocks=load_data(file.getvalue())
except Exception as exc:
    st.error(f"Erro de leitura: {exc}")
    st.stop()

p=st.selectbox("Produto",list(MODEL),format_func=lambda x:f"{x} · {MODEL[x]} · {SHEETS[x]}")
sheet=SHEETS[p]
revlist=sorted(set(blocks[sheet]["PV"].index)&set(blocks[sheet]["PROD"].index)&set(blocks[sheet]["EST"].index))
if not revlist:st.error("Nenhuma revisão com os três blocos completos.");st.stop()
review=st.select_slider("Versão do plano disponível (mês seguinte ao fechamento)",options=revlist,value=revlist[-1],format_func=label)
c=review-1
st.caption(f"Fechamento: {label(c)} · revisão usada: {label(review)} · modelo fixo: {MODEL[p]}")
tab1,tab2,tab3=st.tabs(["Visão operacional","Cenários e lotes","Metodologia e auditoria"])
with st.sidebar:
    st.header("Premissas do estudo")
    method=st.selectbox("Distribuição dos erros",["Normal (0, s)","Bootstrap centralizado"])
    persistent=st.checkbox("Erro persistente (sensibilidade)",value=False)
    st.write("1.000 trajetórias · semente fixa")
    st.write("Faixa P2,5–P97,5 · excesso ≥ 180 dias")
    st.caption("Alterações são análises de sensibilidade, não mudanças automáticas da metodologia.")

try:res=simulate(p,c,blocks,base,method,persistent)
except Exception as exc:
    st.warning(f"Simulação indisponível neste fechamento: {exc}")
    try:
        pv=blocks[sheet]["PV"]
        future=[m for m in sorted(pv.columns) if m>c]
        if future:
            f=forecast(p,future,c,blocks)
            with tab1:
                st.subheader("Previsão central (sem intervalo probabilístico)")
                st.dataframe(pd.DataFrame({"Mês":[label(m) for m in future],"Previsão (un.)":np.round(f)}),hide_index=True,use_container_width=True)
    except Exception as sub:st.error(f"Previsão indisponível: {sub}")
    st.stop()

q=lambda x:np.percentile(x,[2.5,50,97.5],axis=0)
dp=q(res["dm"]);ep=q(res["stock"]);cp=q(res["cov"])
ex=(res["cov"]>=LIM).mean(axis=0)
ru=(res["lost"]>0).mean(axis=0)
valid=res["active"]
baseimpact=impacts(res,p,res["production"],{"excesso":0.0,"ruptura":0.0})
ltm=res["ltm"];window=res["window"]
items=[]
for j,m in enumerate(res["months"]):
    warning=bool(valid[j] and (ex[j]>.025 or ru[j]>.025))
    if not warning: action="Monitoramento"
    elif ex[j]>.025 and any((k>=ltm and k<=j and res["production"][k]>0) for k in range(len(res["months"]))): action="Fornecedor"
    elif ex[j]>.025:action="Comercial"
    elif ru[j]>.025 and any(k>=ltm and k<=j and res["production"][k]>0 for k in range(len(res["months"]))):action="Fornecedor"
    else:action="Monitoramento / alocação"
    items.append({"Mês":label(m),"Previsão":round(res["center"][j]),"P2,5":round(dp[0,j]),"P50":round(dp[1,j]),"P97,5":round(dp[2,j]),
                  "Estoque P50":round(ep[1,j]),"Cobertura P50 (dias)":round(cp[1,j]),
                  "P(excesso)":round(float(ex[j])*100,1),"P(ruptura)":round(float(ru[j])*100,1),
                  "Janela crítica":"Sim" if valid[j] else "Não","Encaminhamento":action})
df=pd.DataFrame(items)
with tab1:
    a,b,d,e=st.columns(4)
    a.metric("Modelo",MODEL[p]);b.metric("Lead time",f"{ltm} meses")
    d.metric("Janela crítica",f"{window} meses");e.metric("Sacola de erros",f"{len(res['errors'])} previsões")
    if p=="P2":st.warning("P2: seleção MEA provisória; histórico de arranque insuficiente para validação conclusiva.")
    if np.isfinite(np.mean(res["errors"])) and abs(np.mean(res["errors"]))>1e-6:st.caption(f"Viés histórico observado (realizado − previsto): {fmt(np.mean(res['errors']))} unidades. A Normal pressupõe erro médio zero; não elimina o viés.")
    st.subheader("Previsão e faixa de demanda")
    labels=[label(m) for m in res["months"]]
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=labels,y=dp[2],mode="lines",line=dict(width=0),showlegend=False))
    fig.add_trace(go.Scatter(x=labels,y=dp[0],mode="lines",fill="tonexty",fillcolor="rgba(236,72,153,.16)",line=dict(width=0),name="P2,5–P97,5"))
    fig.add_trace(go.Scatter(x=labels,y=res["center"],name=f"Previsão {MODEL[p]}",line=dict(color="#f6b36b",width=3)))
    fig.add_trace(go.Scatter(x=labels,y=dp[1],name="P50 simulado",line=dict(color="#fff",dash="dot")))
    fig.update_layout(template="plotly_dark",height=310,margin=dict(l=20,r=20,t=12,b=10),paper_bgcolor="#111",plot_bgcolor="#111")
    st.plotly_chart(fig,use_container_width=True)
    st.subheader("Probabilidades e encaminhamento por mês")
    st.dataframe(df,hide_index=True,use_container_width=True)
    st.caption("Gatilhos somente na janela crítica: P97,5 da cobertura ≥ 180 dias ou P97,5 da venda perdida > 0. Probabilidades não são garantias; o histórico de ruptura teve alarmes falsos.")
with tab2:
    st.subheader("Impacto de alterações nos lotes")
    st.caption("Somente lotes com mês de entrega além do lead time podem ser modificados no teste. Mesmos cenários de demanda em todas as alternativas.")
    rows=[]
    for j,m in enumerate(res["months"]):
        volume=res["production"][j]
        if volume<=0:continue
        eligible=j>=ltm
        rows.append({"Mês":label(m),"Produção":round(volume),"Prazo teórico":label(m-ltm),
                     "Alterável pelo LT":"Sim" if eligible else "Não"})
    lots=pd.DataFrame(rows)
    if lots.empty:st.info("Não há lotes de produção planejados. Analisar ação comercial e monitoramento.")
    else:
        st.dataframe(lots,hide_index=True,use_container_width=True)
        editable=[j for j,v in enumerate(res["production"]) if v>0 and j>=ltm]
        if not editable:st.warning("Nenhum lote ainda está fora do lead time. Alterações de fornecedor não são viáveis pelo critério temporal.")
        else:
            j=st.selectbox("Lote para avaliação",editable,format_func=lambda k:f"{label(res['months'][k])} · {fmt(res['production'][k])} un.")
            options={"Manter":None,"Reduzir 25%":-.25,"Reduzir 50%":-.5,"Cancelar":-1.0,"Aumentar 25%":.25,"Adiar 1 mês":"adiar","Antecipar 1 mês":"antecipar"}
            output=[]
            for action,delta in options.items():
                if action=="Manter":plan=res["production"].copy()
                else:
                    plan=res["production"].copy()
                    if delta=="adiar":
                        if j+1>=len(plan):continue
                        plan[j]=0;plan[j+1]+=res["production"][j]
                    elif delta=="antecipar":
                        if j-1<ltm:continue
                        plan[j]=0;plan[j-1]+=res["production"][j]
                    else:plan[j]*=1+delta
                met=impacts(res,p,plan,baseimpact)
                output.append({"Alternativa":action,"P(excesso na janela)":f"{met['excesso']:.1%}","P(ruptura na janela)":f"{met['ruptura']:.1%}",
                               "Δ excesso (p.p.)":round(100*met["delta_excesso"],1),"Δ ruptura (p.p.)":round(100*met["delta_ruptura"],1)})
            st.dataframe(pd.DataFrame(output),hide_index=True,use_container_width=True)
            st.caption("As mudanças são cenários hipotéticos: não validam contratos, lote mínimo ou capacidade produtiva. Não há otimização automática.")
with tab3:
    st.subheader("Rastreabilidade")
    st.write("Origem rolante: no fechamento c só é usado o realizado do mês m registrado na revisão m+1, com m ≤ c.")
    st.write("P1: MEA-P; P2: MEA (provisório); P3: Oficial. A seleção de modelos foi fixada no estudo, não reotimizada no painel.")
    st.write("MEA e MEA-P: média em log10 das séries expandidas pelos análogos; MEA-P ajusta o pipe M1–M3.")
    st.write("Simulação padrão: demanda = max(0, previsão + Normal(0,s)); s amostral da sacola de erros do arranque; 1.000 trajetórias.")
    st.write("Estoque: max(0, estoque anterior + produção − demanda), com vendas não atendidas perdidas; cobertura pelo consumo futuro.")
    st.write("Parâmetros: 180 dias (L'Oréal); LT da aba Base; janela = ceil(LT×7/30) + ceil(cobertura alvo/30) + 1.")
    st.write("Limitações: amostra pequena, erros sobrepostos, Normal não comprovada, plano termina em dezembro/2026, operacionalidade dos lotes não confirmada.")
    st.caption("O painel é um instrumento de apoio, não uma liberação de ordem de compra/produção. As decisões exigem validação humana.")
    with st.expander("Sacola de erros conhecida neste fechamento"):
        st.dataframe(pd.DataFrame({"Erro (un.)":res["errors"]}),hide_index=True)
    st.download_button("Baixar análise mensal (CSV)",df.to_csv(index=False).encode("utf-8-sig"),file_name=f"smartlaunch_{p}_{c}.csv",mime="text/csv")

# Diagnóstico da versão de dados: não utilizar informações de revisões futuras.
# Os testes automatizados verificam leitura, previsão e simulação em todas as famílias de produto.
