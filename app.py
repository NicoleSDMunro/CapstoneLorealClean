import re
import html
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

try:
    from statsforecast import StatsForecast
    from statsforecast.models import AutoETS
    STATSFORECAST_OK = True
except Exception:
    STATSFORECAST_OK = False

st.set_page_config(page_title="Smart Launch | Supply Chain", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&display=swap');
html,body,[class*="css"]{font-family:'Helvetica Neue',Helvetica,Arial,sans-serif}.stApp{background:#000;color:#f5f5f5}.block-container{padding-top:.25rem;max-width:1188px}[data-testid="stHeader"]{background:transparent}#MainMenu,footer{visibility:hidden}.hero-kicker{font-size:11px;font-weight:300;letter-spacing:.18em;text-transform:uppercase;color:#8c8c8c;margin-bottom:8px}.hero-title{font-family:'Barlow Condensed','Helvetica Neue',Helvetica,Arial,sans-serif;font-size:34px;line-height:1;font-weight:700;letter-spacing:.04em;text-transform:uppercase;margin-bottom:10px;color:#fff;white-space:nowrap;overflow:hidden}.hero-subtitle{color:#9ca3af;font-size:13px;font-weight:300;margin-bottom:30px}.empty-panel{background:#101010;border:1px dashed #3a3a3a;border-radius:10px;padding:34px 28px;margin-top:22px}.empty-title{font-size:24px;font-weight:850;margin-bottom:8px}.empty-text{color:#a5a5a5;font-size:15px;line-height:1.6}.stSelectbox label{color:#60646f!important;text-transform:uppercase;letter-spacing:.08em;font-size:11px!important;font-weight:400}.stSelectbox [data-baseweb="select"]>div{background:#151515!important;border:1px solid #333!important;border-radius:6px!important;color:#e5e7eb!important;min-height:42px}.stSelectbox [data-baseweb="select"] span{color:#e5e7eb!important;font-size:14px!important;font-weight:400}.info-card{height:96px;background:#111;border:.5px solid #2a2a2a;border-radius:6px;box-sizing:border-box;padding:16px 18px;display:flex;flex-direction:column;justify-content:center}.info-label{color:#555;font-size:10px;font-weight:400;letter-spacing:.07em;text-transform:uppercase;line-height:1;margin-bottom:12px}.info-value{font-size:18px;font-weight:600;line-height:1.05;white-space:nowrap}.info-sub{color:#999;font-size:11px;font-weight:400;line-height:1.2;margin-top:9px;white-space:nowrap}.orange{color:#e8a24a}.red{color:#f05a5f}.green{color:#1ca37e}.yellow{color:#f4c21f}.tab-single{margin:34px 0 22px}.tab-single span{display:inline-block;padding:0 26px 14px;text-transform:uppercase;letter-spacing:.07em;font-size:13px;font-weight:600;color:#fff;border-bottom:4px solid #fff}.review-title{font-size:16px;font-weight:600;letter-spacing:.02em;margin:10px 0 18px}.month-row div[data-testid="stButton"] button,[data-testid="stButton"] button[kind="secondary"]{height:42px!important;border-radius:8px!important;border:1px solid #333!important;background:#171717!important;color:#d1d5db!important;font-size:13px!important;font-weight:300!important;box-shadow:none!important}.month-row div[data-testid="stButton"] button p,[data-testid="stButton"] button[kind="secondary"] p{color:#d1d5db!important;font-size:13px!important;font-weight:300!important}.month-row div[data-testid="stButton"] button[kind="primary"]{background:var(--accent)!important;color:#fff!important;border-color:var(--accent)!important;font-weight:700!important}.month-row div[data-testid="stButton"] button[kind="primary"] p{color:#fff!important;font-weight:700!important}.section-title{color:#9a9a9a;text-transform:uppercase;letter-spacing:.08em;font-size:12px;font-weight:400;margin:24px 0 10px}.chart-card,.table-wrap{background:#101010;border:1px solid #2a2a2a;border-radius:8px;padding:12px;margin-bottom:14px}.alert-box,.warn-box,.success-box{border-radius:8px;padding:16px 20px;color:#fff;font-size:13px;line-height:1.6;margin-bottom:10px}.alert-box{background:linear-gradient(90deg,rgba(239,68,68,.22),rgba(239,68,68,.05));border-left:6px solid #ef4444}.warn-box{background:linear-gradient(90deg,rgba(250,204,21,.18),rgba(250,204,21,.04));border-left:6px solid #facc15}.success-box{background:linear-gradient(90deg,rgba(22,163,123,.20),rgba(22,163,123,.04));border-left:6px solid #16a37b}.trigger-pills,.legend-row,.decision-summary{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0 14px}.trigger-pill-red,.trigger-pill-orange,.trigger-pill-yellow,.legend-chip,.decision-chip{border:1px solid #303030;border-radius:999px;padding:8px 13px;background:#0b0b0b;font-size:12px;color:#d1d5db}.trigger-pill-red{border-color:#ef4444;color:#ef4444}.trigger-pill-orange{border-color:#f97316;color:#f97316}.trigger-pill-yellow{border-color:#d49100;color:#d49100}.legend-chip strong{color:#fff}.dark-table{width:100%;border-collapse:separate;border-spacing:0;border-radius:8px;border:1px solid #2a2a2a;background:#111;overflow:hidden}.dark-table th{background:#1a1a1a;color:#9ca3af;text-align:left;padding:11px 10px;font-size:11px;font-weight:500;text-transform:uppercase;border-bottom:1px solid #2a2a2a}.dark-table td{background:#111;color:#d1d5db;padding:10px;font-size:11px;font-weight:400;border-bottom:1px solid #242424;vertical-align:top}.dark-table tr:last-child td{border-bottom:0}.dark-table tr.green td{background:rgba(34,197,94,.10)}.dark-table tr.yellow td{background:rgba(250,204,21,.11)}.dark-table tr.orange td{background:rgba(249,115,22,.12)}.dark-table tr.red td{background:rgba(239,68,68,.13)}.dark-table .status{font-weight:800;color:#f5f5f5;white-space:nowrap}.metric-note,.decision-note{color:#9ca3af;font-size:12px;line-height:1.5;margin:0 0 12px}
</style>
""", unsafe_allow_html=True)

MESES=["jun/25","jul/25","ago/25","set/25","out/25","nov/25","dez/25","jan/26","fev/26","mar/26","abr/26","mai/26","jun/26"]
REVISOES=MESES[:9]
PRODUTOS=list("ABCDEFGHIJKLMNOP")
MONTH_MAP={"jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,"jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12}
ALERT_COLORS={"vermelho":"#ef4444","laranja":"#f97316","amarelo":"#d49100","verde":"#22c55e"}
ALERT_LABELS={"vermelho":"🔴 Vermelho","laranja":"🟠 Laranja","amarelo":"🟡 Amarelo","verde":"🟢 Sem excesso"}
ALERT_CLASS={"🔴 Vermelho":"red","🟠 Laranja":"orange","🟡 Amarelo":"yellow","🟢 Sem excesso":"green"}


def mes_to_period(x):
    s=str(x).strip().lower();m=re.search(r"(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[\-/ ]?(\d{2,4})",s)
    if not m:return None
    ano=int(m.group(2));ano=2000+ano if ano<100 else ano
    return pd.Period(year=ano,month=MONTH_MAP[m.group(1)],freq="M")


def period_label(p):
    inv={v:k for k,v in MONTH_MAP.items()};return f"{inv[p.month]}/{str(p.year)[-2:]}"


def find_header_row(raw):
    for i in range(min(len(raw),30)):
        if sum(mes_to_period(v) is not None for v in raw.iloc[i].tolist())>=5:return i
    return None


def find_blocks(raw):
    blocks={}
    for i in range(len(raw)):
        text=" ".join([str(v).upper() for v in raw.iloc[i].tolist() if pd.notna(v)])
        if "PV" in text and ("SELL" in text or "SEL" in text):blocks["PV"]=i
        elif "PRODU" in text:blocks["Producao"]=i
        elif "ESTOQUE" in text:blocks["Estoque"]=i
    return blocks


def parse_product_sheet(xls,product):
    raw=pd.read_excel(xls,sheet_name=product,header=None);blocks=find_blocks(raw)
    if len(blocks)<3:raise ValueError(f"Não encontrei os 3 blocos na aba {product}.")
    out=[];ordered=sorted(blocks.items(),key=lambda kv:kv[1])
    for idx,(var,start) in enumerate(ordered):
        end=ordered[idx+1][1] if idx+1<len(ordered) else len(raw)
        sub=raw.iloc[start+1:end].dropna(how="all");hrel=find_header_row(sub.reset_index(drop=True))
        if hrel is None:continue
        header_idx=sub.index[hrel]
        target_cols=[(j,mes_to_period(v)) for j,v in enumerate(raw.iloc[header_idx].tolist()) if mes_to_period(v) is not None]
        if not target_cols:continue
        label_col=max(0,target_cols[0][0]-1)
        for r in range(header_idx+1,end):
            revp=mes_to_period(raw.iat[r,label_col])
            if revp is None:continue
            for j,tp in target_cols:
                val=pd.to_numeric(raw.iat[r,j],errors="coerce")
                if pd.notna(val):out.append({"Produto":product,"Variavel":var,"Revisao":period_label(revp),"Mes":period_label(tp),"Valor":float(val)})
    return pd.DataFrame(out)


def parse_sheet(xls,name):
    try:
        df=pd.read_excel(xls,sheet_name=name);df.columns=[str(c).strip() for c in df.columns];return df
    except Exception:return pd.DataFrame()


def col_like(df,keys):
    for c in df.columns:
        if all(k.lower() in str(c).lower() for k in keys):return c
    return None


def produto_info(base_df,bom_df,produto,estoque_final):
    info={"Origem":"-","CoberturaTargetDias":75,"HBdias":60,"LTSemanas":16,"Demanda":"-","EstoqueFinal":estoque_final}
    if not base_df.empty:
        pcol=base_df.columns[1] if len(base_df.columns)>1 else base_df.columns[0]
        row=base_df[base_df[pcol].astype(str).str.upper().str.strip().eq(produto.upper())]
        if row.empty:
            pcol_alt=col_like(base_df,["produto"]) or base_df.columns[0]
            row=base_df[base_df[pcol_alt].astype(str).str.upper().str.strip().eq(produto.upper())]
        if not row.empty:
            row=row.iloc[0]
            if len(base_df.columns)>2 and pd.notna(row.iloc[2]):info["Origem"]=row.iloc[2]
            if len(base_df.columns)>11 and pd.notna(row.iloc[11]):info["Demanda"]=row.iloc[11]
            for key,names in {"CoberturaTargetDias":["cobertura"],"HBdias":["hb"]}.items():
                c=col_like(base_df,names)
                if c is not None and pd.notna(row[c]):info[key]=row[c]
    if not bom_df.empty:
        pcol=col_like(bom_df,["produto"]) or bom_df.columns[0];ltcol=col_like(bom_df,["lt"]) or col_like(bom_df,["lead"])
        if ltcol is not None:
            vals=pd.to_numeric(bom_df[bom_df[pcol].astype(str).str.upper().str.strip().eq(produto.upper())][ltcol],errors="coerce").dropna()
            if len(vals):info["LTSemanas"]=float(vals.max())
    return info


def mean_last(series,idx,n):
    vals=pd.to_numeric(series.iloc[max(0,idx-n+1):idx+1],errors="coerce").dropna()
    return vals.mean() if len(vals) else np.nan


def std_last(series,idx,n):
    vals=pd.to_numeric(series.iloc[max(0,idx-n+1):idx+1],errors="coerce").dropna()
    return vals.std(ddof=0) if len(vals)>1 else 0


def classify_metrics(row):
    desvio=row["Desvio vs Target"];trend=row["Tendência"];gap=row["Gap Produção x Venda"];hb=row["HB Stress"];vol=row["Volatilidade"];ltp=row["LT Protection"]
    desvio_cls="crítico" if desvio>0.40 else "médio" if desvio>0.15 else "leve"
    trend_cls="queda" if trend<-0.10 else "aumento" if trend>0.10 else "estável"
    gap_cls="produção abaixo" if gap<-0.20 else "produção acima" if gap>0.20 else "balanceada"
    hb_cls="crítico" if hb>1.0 else "atenção" if hb>=0.8 else "seguro"
    vol_cls="alta" if vol>0.35 else "média" if vol>=0.20 else "baixa"
    lt_cls="alta" if ltp>1.5 else "média" if ltp>=1.0 else "baixa"
    veto=None
    if hb_cls=="crítico" and (desvio>0 or gap_cls!="produção abaixo"):
        veto="V1 - Stress crítico de HB"
    elif desvio_cls=="crítico" and trend_cls=="queda":
        veto="V2 - Excesso elevado com demanda em queda"
    elif desvio_cls=="crítico" and gap_cls=="produção acima":
        veto="V3 - Excesso elevado alimentado pela operação"
    elif desvio_cls=="médio" and trend_cls=="queda" and hb_cls in ["atenção","crítico"]:
        veto="V4 - Excesso relevante em agravamento"
    score={"leve":1,"médio":2,"crítico":3}[desvio_cls]+{"aumento":0,"estável":1,"queda":2}[trend_cls]+{"produção abaixo":0,"balanceada":1,"produção acima":2}[gap_cls]+{"seguro":0,"atenção":2,"crítico":3}[hb_cls]+{"baixa":0,"média":1,"alta":1}[vol_cls]+{"baixa":-1,"média":0,"alta":1}[lt_cls]
    obs=""
    if veto:alerta="vermelho"
    elif hb_cls=="crítico" and trend_cls=="queda":alerta="laranja";obs="HB crítico sem veto: demanda cai, mas a operação/target moderam a leitura."
    elif score>=6:alerta="laranja"
    elif score>=4:alerta="amarelo"
    else:alerta="verde"
    if alerta=="verde" and gap_cls=="produção acima" and desvio<=0 and hb<1:
        obs="Sem excesso, mas há pressão inicial por produção acima da venda."
    if trend_cls=="aumento" and alerta in ["amarelo","laranja"]:
        obs=(obs+" " if obs else "")+"Trend positivo reduz risco; alerta vem de HB/gap/cobertura."
    return pd.Series({"Desvio classe":desvio_cls,"Tendência classe":trend_cls,"Gap classe":gap_cls,"HB classe":hb_cls,"Vol classe":vol_cls,"LT classe":lt_cls,"Score":score,"Regra crítica":veto or "-","Alerta":alerta,"Observação":obs or "-"})


def build_analytical_metrics(pivot,target,hb,lt_sem):
    df=pivot.set_index("Mes").reindex(MESES)
    pv=df["PV"] if "PV" in df else pd.Series(index=MESES,dtype=float)
    prod=df["Producao"] if "Producao" in df else pd.Series(index=MESES,dtype=float)
    est=df["Estoque"] if "Estoque" in df else pd.Series(index=MESES,dtype=float)
    rows=[]
    for i,mes in enumerate(MESES):
        pv3=mean_last(pv,i,3);pv6=mean_last(pv,i,6);prod3=mean_last(prod,i,3);vol6=std_last(pv,i,6)
        cobertura=(est.iloc[i]/(pv3/30)) if pd.notna(est.iloc[i]) and pd.notna(pv3) and pv3 else np.nan
        desvio=((cobertura-target)/target) if target else np.nan
        trend=((pv3-pv6)/pv6) if pd.notna(pv3) and pd.notna(pv6) and pv6 else 0
        vol=(vol6/pv6) if pd.notna(pv6) and pv6 else 0
        gap=((prod3-pv3)/pv3) if pd.notna(prod3) and pd.notna(pv3) and pv3 else 0
        ltprot=(cobertura/(lt_sem*7)) if pd.notna(cobertura) and lt_sem else np.nan
        hbstress=(cobertura/hb) if pd.notna(cobertura) and hb else np.nan
        rows.append({"Mês":mes,"PV":pv.iloc[i],"Produção":prod.iloc[i],"Estoque":est.iloc[i],"Cobertura Observada":cobertura,"Desvio vs Target":desvio,"Tendência":trend,"Volatilidade":vol,"Gap Produção x Venda":gap,"LT Protection":ltprot,"HB Stress":hbstress})
    out=pd.DataFrame(rows)
    return pd.concat([out,out.apply(classify_metrics,axis=1)],axis=1)


def generate_excess_triggers(metrics):
    rows=[]
    for _,r in metrics[metrics["Alerta"].isin(["vermelho","laranja","amarelo"])].iterrows():
        tipo={"vermelho":"Excesso severo","laranja":"Excesso relevante","amarelo":"Em formação"}[r["Alerta"]]
        detalhe=f"Cobertura {r['Cobertura Observada']:.0f}d, desvio {r['Desvio vs Target']*100:.0f}% vs target, tendência {r['Tendência classe']} e gap {r['Gap classe']}."
        rows.append({"Mês":r["Mês"],"Tipo":tipo,"Nível":r["Alerta"],"Cor":ALERT_COLORS[r["Alerta"]],"Detalhe":detalhe,"PV":r["PV"],"Produção":r["Produção"],"Estoque":r["Estoque"]})
    return pd.DataFrame(rows)


def build_autoets_forecast(pivot,rev):
    if "PV" not in pivot.columns:return None,"Sem coluna PV para treinar o AutoETS."
    y=pd.to_numeric(pivot.set_index("Mes").reindex(MESES)["PV"],errors="coerce")
    cutoff=MESES.index(rev) if rev in MESES else 0
    train=y.iloc[:cutoff+1].dropna()
    future_months=MESES[cutoff+1:]
    if len(future_months)==0:return None,"Não há meses futuros depois da revisão selecionada."
    if len(train)<4:return None,"Selecione uma revisão a partir de set/25 para ter ao menos 4 meses de histórico para o AutoETS."
    h=len(future_months)
    method="AutoETS"
    try:
        if not STATSFORECAST_OK:raise ImportError("statsforecast não instalado")
        train_df=pd.DataFrame({"unique_id":"PV","ds":pd.date_range("2025-06-01",periods=len(train),freq="MS"),"y":train.values})
        sf=StatsForecast(models=[AutoETS(season_length=1,alias="AutoETS")],freq="MS")
        fcst=sf.forecast(df=train_df,h=h)
        pred=pd.to_numeric(fcst["AutoETS"],errors="coerce").values
    except Exception:
        x=np.arange(len(train));coef=np.polyfit(x,train.values,1);pred=np.maximum(0,np.polyval(coef,np.arange(len(train),len(train)+h)));method="Tendência linear fallback"
    out=pd.DataFrame({"Mês":future_months,"PV planejado":y.reindex(future_months).values,"Forecast estatístico":pred})
    out["Diferença"]=(out["Forecast estatístico"]-out["PV planejado"])/out["PV planejado"].replace(0,np.nan)
    return out,method


def calculate_decision_window(trigger_row,revisao_mes,hb_dias,lt_sem,po_emitido="Não",po_status="Aberto"):
    rev_period=mes_to_period(revisao_mes);trigger_period=mes_to_period(trigger_row["Mês"])
    lt_dias=float(lt_sem)*7;dias_ate=max(0,int((trigger_period-rev_period).n*30)) if rev_period and trigger_period else 0
    dentro_hb=dias_ate<=hb_dias;dentro_lt=dias_ate<=lt_dias;entrando_lt=lt_dias<dias_ate<=lt_dias+30;po_confirmado=po_emitido=="Sim" and po_status in ["Em produção","Em trânsito"]
    if dentro_hb or dentro_lt or po_confirmado:estado,emoji,classe,texto="EXCESSO COMPROMETIDO","🔴","red","Comprometido: compras/produção já estão travadas por HB, LT ou PO confirmado."
    elif entrando_lt:estado,emoji,classe,texto="ÚLTIMA JANELA","🟡","yellow","Ainda dá para agir, mas está entrando no LT. A decisão é possível com risco."
    else:estado,emoji,classe,texto="AÇÃO POSSÍVEL","🟢","green","Ainda dá para agir: o gatilho está fora do HB e fora do LT."
    return {"Mês do gatilho":trigger_row["Mês"],"Status decisão":f"{emoji} {estado}","HB":f"{'Dentro' if dentro_hb else 'Fora'} ({dias_ate}d / {hb_dias:.0f}d)","LT":f"{'Dentro' if dentro_lt else 'Última janela' if entrando_lt else 'Fora'} ({dias_ate}d / {lt_dias:.0f}d)","PO":f"Sim — {po_status}" if po_emitido=="Sim" else "Não informado/Não emitido","Interpretação":texto,"Classe":classe}


def fmt(v):
    if pd.isna(v):return "-"
    v=float(v)
    if abs(v)>=1_000_000:return f"{v/1_000_000:.1f}M"
    if abs(v)>=1000:return f"{v:,.0f}".replace(",",".")
    return f"{v:.0f}"


def pct(v):return "-" if pd.isna(v) else f"{float(v)*100:.0f}%"

def cor_revisao(rev):
    if str(rev).startswith("jun"):return "#5b9cff"
    if str(rev).startswith("jul"):return "#16a37b"
    if str(rev).startswith("ago"):return "#e5533f"
    return "#f4474c"


def info_card(label,value,sub,cls):
    st.markdown(f'<div class="info-card"><div class="info-label">{html.escape(str(label))}</div><div class="info-value {cls}">{html.escape(str(value))}</div><div class="info-sub">{html.escape(str(sub))}</div></div>',unsafe_allow_html=True)


def render_table(df,cols,class_col=None):
    head="".join([f"<th>{html.escape(c)}</th>" for c in cols]);rows=""
    for _,r in df.iterrows():
        raw=str(r[class_col]) if class_col and class_col in r else ""
        klass=ALERT_CLASS.get(raw,raw).replace("vermelho","red").replace("laranja","orange").replace("amarelo","yellow").replace("verde","green")
        rows+=f"<tr class='{html.escape(klass)}'>"+"".join([f"<td class='{'status' if 'Status' in c or c=='Alerta' else ''}'>{html.escape(str(r[c]))}</td>" for c in cols])+"</tr>"
    st.markdown(f"<table class='dark-table'><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>",unsafe_allow_html=True)


with st.sidebar:
    st.header("Base de dados")
    arquivo=st.file_uploader("Suba sua base Excel",type=["xlsx"])
    st.caption("Formato esperado: abas Base, BOM e produtos A–P.")

st.markdown('<div class="hero-kicker">L OREAL BRASIL - SUPPLY CHAIN STRATEGY</div>',unsafe_allow_html=True)
st.markdown('<div class="hero-title">SMART LAUNCH & RESPONSIVENESS TO GROWTH</div>',unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Produtos A-E · Jun/2025-Jun/2026</div>',unsafe_allow_html=True)

if arquivo is None:
    st.markdown('<div class="empty-panel"><div class="empty-title">Nenhuma base carregada</div><div class="empty-text">Envie um arquivo Excel no menu lateral para liberar o dashboard.</div></div>',unsafe_allow_html=True);st.stop()

try:
    xls=pd.ExcelFile(arquivo);base_df=parse_sheet(xls,"Base");bom_df=parse_sheet(xls,"BOM");partes=[];erros=[]
    for p in [s for s in xls.sheet_names if str(s).strip().upper() in PRODUTOS]:
        try:partes.append(parse_product_sheet(xls,p.strip().upper()))
        except Exception as e:erros.append(str(e))
    if not partes:
        st.error("Não consegui extrair as abas de produto.")
        if erros:st.code("\n".join(erros[:6]))
        st.stop()
    long_df=pd.concat(partes,ignore_index=True)
except Exception as e:
    st.error("Não foi possível ler a base enviada.");st.code(str(e));st.stop()

produtos=sorted(long_df["Produto"].unique());options=[]
for p in produtos:
    piv=long_df[(long_df["Produto"]==p)&(long_df["Revisao"]==REVISOES[-1])].pivot_table(index="Mes",columns="Variavel",values="Valor",aggfunc="sum").reindex(MESES)
    est=piv["Estoque"].dropna().iloc[-1] if "Estoque" in piv and len(piv["Estoque"].dropna()) else 0;inf=produto_info(base_df,bom_df,p,est)
    options.append(f"Produto {p} - {inf['Origem']} - Cob.T {float(pd.to_numeric(inf['CoberturaTargetDias'],errors='coerce') or 75):.0f}d - LT {float(pd.to_numeric(inf['LTSemanas'],errors='coerce') or 16):.0f}sem - {inf['Demanda']}")

sel=st.selectbox("Produto",options,index=0)
produto=re.search(r"Produto ([A-P])",sel).group(1);base_prod=long_df[long_df["Produto"]==produto]
revisoes=[m for m in REVISOES if m in set(base_prod["Revisao"])] or sorted(base_prod["Revisao"].unique())
if "revisao" not in st.session_state or st.session_state.revisao not in revisoes:st.session_state.revisao=revisoes[0]
rev=st.session_state.revisao;st.markdown(f"<style>:root{{--accent:{cor_revisao(rev)};}}</style>",unsafe_allow_html=True)

pivot=base_prod[base_prod["Revisao"]==rev].pivot_table(index="Mes",columns="Variavel",values="Valor",aggfunc="sum").reindex(MESES).reset_index()
est_final=pivot["Estoque"].dropna().iloc[-1] if "Estoque" in pivot and len(pivot["Estoque"].dropna()) else 0;info=produto_info(base_df,bom_df,produto,est_final)
lt_sem=float(pd.to_numeric(info["LTSemanas"],errors="coerce") if pd.notna(info["LTSemanas"]) else 16);lt_dias=int(round(lt_sem*7));lt_meses=lt_dias/30
ct_dias=float(pd.to_numeric(info["CoberturaTargetDias"],errors="coerce") if pd.notna(info["CoberturaTargetDias"]) else 75);hb_dias=float(pd.to_numeric(info["HBdias"],errors="coerce") if pd.notna(info["HBdias"]) else 60)
lt_cls="red" if lt_sem>16 else "orange" if lt_sem>10 else "green";ct_cls="red" if lt_dias>ct_dias else "green";dem_cls="red" if "queda" in str(info["Demanda"]).lower() else "green";est_cls="red" if est_final<0 else ""

scols=st.columns(5,gap="small");cards=[("ORIGEM",info["Origem"],"","orange"),("LT MAX",f"{lt_sem:.0f} sem",f"aprox {lt_meses:.1f}m - {lt_dias}d",lt_cls),("COB. TARGET",f"{ct_dias:.0f}d",f"aprox {ct_dias/30:.1f}m - {ct_dias/7:.1f}sem",ct_cls),("DEMANDA",info["Demanda"],"",dem_cls),("EST. FINAL",fmt(est_final),"última rev - jun/26",est_cls)]
for i,(lab,val,sub,cls) in enumerate(cards):
    with scols[i]:info_card(lab,val,sub,cls)

st.markdown('<div class="tab-single"><span>VISAO POR REVISAO</span></div>',unsafe_allow_html=True)
st.markdown(f'<div class="review-title">REVISAO: <span style="color:var(--accent)">{rev}</span></div>',unsafe_allow_html=True)
cols=st.columns(len(revisoes)+2,gap="small");st.markdown('<div class="month-row">',unsafe_allow_html=True)
for i,mes in enumerate(revisoes):
    with cols[i]:
        if st.button(mes,key=f"rev_{mes}",type="primary" if mes==rev else "secondary",use_container_width=True):st.session_state.revisao=mes;st.rerun()
with cols[-2]:
    if st.button("<",use_container_width=True):st.session_state.revisao=revisoes[max(0,revisoes.index(rev)-1)];st.rerun()
with cols[-1]:
    if st.button(">",use_container_width=True):st.session_state.revisao=revisoes[min(len(revisoes)-1,revisoes.index(rev)+1)];st.rerun()
st.markdown('</div>',unsafe_allow_html=True)

metrics=build_analytical_metrics(pivot,ct_dias,hb_dias,lt_sem)
excess_triggers=generate_excess_triggers(metrics)

if not excess_triggers.empty:
    red_count=int((excess_triggers["Nível"]=="vermelho").sum());orange_count=int((excess_triggers["Nível"]=="laranja").sum());yellow_count=int((excess_triggers["Nível"]=="amarelo").sum())
    st.markdown(f'<div class="trigger-pills"><span class="trigger-pill-red">🔴 Excesso severo&nbsp; <strong>{red_count}</strong></span><span class="trigger-pill-orange">🟠 Excesso relevante&nbsp; <strong>{orange_count}</strong></span><span class="trigger-pill-yellow">🟡 Em formação&nbsp; <strong>{yellow_count}</strong></span></div>',unsafe_allow_html=True)

st.markdown('<div class="section-title">METRICAS ANALITICAS DE EXCESSO</div>',unsafe_allow_html=True)
metric_view=metrics.copy();metric_view=metric_view[metric_view["Mês"].isin(MESES)]
metric_view["Cobertura"]=metric_view["Cobertura Observada"].apply(lambda x:"-" if pd.isna(x) else f"{x:.0f}d")
metric_view["Desvio"]=metric_view["Desvio vs Target"].apply(pct);metric_view["Trend"]=metric_view["Tendência"].apply(pct);metric_view["Gap"]=metric_view["Gap Produção x Venda"].apply(pct)
metric_view["HB"]=metric_view["HB Stress"].apply(lambda x:"-" if pd.isna(x) else f"{x:.2f}");metric_view["LT Prot."]=metric_view["LT Protection"].apply(lambda x:"-" if pd.isna(x) else f"{x:.2f}")
metric_view["ClasseLinha"]=metric_view["Alerta"].map({"vermelho":"red","laranja":"orange","amarelo":"yellow","verde":"green"});metric_view["Alerta"]=metric_view["Alerta"].map(ALERT_LABELS)
st.markdown('<div class="table-wrap"><p class="metric-note"><strong>Painel de excesso:</strong> verde significa sem excesso/sobrecobertura, não saúde geral do SKU. Hierarquia: primeiro verifica regra crítica; se não houver, calcula score.</p>',unsafe_allow_html=True)
st.markdown('<div class="legend-row"><span class="legend-chip"><strong>Regra crítica</strong> → vermelho direto</span><span class="legend-chip"><strong>Score 0–3</strong> → sem excesso</span><span class="legend-chip"><strong>Score 4–5</strong> → amarelo</span><span class="legend-chip"><strong>Score ≥ 6</strong> → laranja</span></div>',unsafe_allow_html=True)
render_table(metric_view[["Mês","Cobertura","Desvio","Trend","Gap","HB","LT Prot.","Score","Alerta","Regra crítica","Observação","ClasseLinha"]],["Mês","Cobertura","Desvio","Trend","Gap","HB","LT Prot.","Score","Alerta","Regra crítica","Observação"],class_col="ClasseLinha")
st.markdown('</div>',unsafe_allow_html=True)

st.markdown('<div class="section-title">FORECAST ESTATISTICO AUTOETS</div>',unsafe_allow_html=True)
forecast_df,forecast_method=build_autoets_forecast(pivot,rev)
st.markdown('<div class="table-wrap"><p class="metric-note">O AutoETS usa o PV observado até a revisão selecionada como histórico e projeta os meses restantes. A comparação abaixo mostra se o PV planejado está acima ou abaixo do forecast estatístico.</p>',unsafe_allow_html=True)
if forecast_df is None:
    st.info(forecast_method)
else:
    view=forecast_df.copy();view["PV planejado"]=view["PV planejado"].apply(fmt);view["Forecast estatístico"]=view["Forecast estatístico"].apply(fmt);view["Diferença"]=view["Diferença"].apply(pct)
    st.markdown(f'<p class="metric-note">Modelo usado: <strong>{forecast_method}</strong>. Em séries curtas, o app usa AutoETS sem sazonalidade; com histórico maior, pode-se evoluir para season_length=12.</p>',unsafe_allow_html=True)
    render_table(view,["Mês","PV planejado","Forecast estatístico","Diferença"])
st.markdown('</div>',unsafe_allow_html=True)

st.markdown(f'<div class="section-title">PV - PRODUCAO - ESTOQUE - {rev.upper()}</div>',unsafe_allow_html=True);st.markdown('<div class="chart-card">',unsafe_allow_html=True)
fig=go.Figure()
for var,color,dash,name in [("PV","#5b9cff","solid","PV (Sell In)"),("Producao","#45c49b","dash","Producao"),("Estoque","#e7895e","dot","Estoque")]:
    if var in pivot:fig.add_trace(go.Scatter(x=pivot["Mes"],y=pivot[var],mode="lines+markers",name=name,line=dict(width=3,color=color,dash=dash),marker=dict(size=7),hovertemplate=f"{name}: %{{y:,.0f}}<extra></extra>"))
if forecast_df is not None:
    fig.add_trace(go.Scatter(x=forecast_df["Mês"],y=forecast_df["Forecast estatístico"],mode="lines+markers",name="AutoETS PV",line=dict(width=2,color="#facc15",dash="dashdot"),marker=dict(size=6),hovertemplate="AutoETS: %{y:,.0f}<extra></extra>"))
if rev in MESES:fig.add_vline(x=rev,line_width=1.5,line_dash="dash",line_color="#6b7280")
if not excess_triggers.empty:
    for _,row in excess_triggers.iterrows():fig.add_vline(x=row["Mês"],line_width=1.5,line_dash="dash",line_color=row["Cor"])
    fig.add_trace(go.Scatter(x=excess_triggers["Mês"],y=excess_triggers["PV"],mode="markers",name="Gatilhos de excesso",marker=dict(size=17,color="rgba(0,0,0,0)",line=dict(color=excess_triggers["Cor"],width=4),symbol="circle"),customdata=np.stack([excess_triggers["Tipo"],excess_triggers["Detalhe"]],axis=-1),hovertemplate="%{customdata[0]}<br>%{customdata[1]}<extra></extra>"))
fig.update_layout(paper_bgcolor="#101010",plot_bgcolor="#101010",font=dict(family="Helvetica Neue, Helvetica, Arial, sans-serif",color="#999",size=11),height=430,margin=dict(l=30,r=18,t=18,b=35),legend=dict(orientation="h",y=-.22,x=.15,font=dict(size=12,color="#999")),xaxis=dict(gridcolor="#202020",zerolinecolor="#202020"),yaxis=dict(gridcolor="#202020",zerolinecolor="#202020"),hovermode="x unified",hoverlabel=dict(bgcolor="#171717",bordercolor="#2a2a2a",font=dict(color="#f5f5f5",size=12)))
st.plotly_chart(fig,use_container_width=True);st.markdown('</div>',unsafe_allow_html=True)

if not excess_triggers.empty:
    st.markdown('<div class="section-title">BLOCO 2 — JANELA DE DECISAO</div>',unsafe_allow_html=True)
    st.markdown('<div class="table-wrap"><p class="decision-note">A Janela de Decisão não cria novos alertas. Ela resume se ainda existe viabilidade de ação para cada gatilho detectado.</p>',unsafe_allow_html=True)
    with st.expander("Inputs opcionais de PO",expanded=False):
        po_emitido=st.selectbox("PO já emitido?",["Não","Sim"],index=0);po_status=st.selectbox("Status do PO",["Aberto","Em produção","Em trânsito"],index=0)
    decision_df=pd.DataFrame([calculate_decision_window(row,rev,hb_dias,lt_sem,po_emitido,po_status) for _,row in excess_triggers.iterrows()])
    counts=decision_df["Status decisão"].str.replace("🟢 ","",regex=False).str.replace("🟡 ","",regex=False).str.replace("🔴 ","",regex=False).value_counts().to_dict()
    st.markdown(f'<div class="decision-summary"><span class="decision-chip">🟢 Ação possível: {counts.get("AÇÃO POSSÍVEL",0)}</span><span class="decision-chip">🟡 Última janela: {counts.get("ÚLTIMA JANELA",0)}</span><span class="decision-chip">🔴 Comprometido: {counts.get("EXCESSO COMPROMETIDO",0)}</span></div>',unsafe_allow_html=True)
    render_table(decision_df,["Mês do gatilho","Status decisão","HB","LT","PO","Interpretação"],class_col="Classe");st.markdown('</div>',unsafe_allow_html=True)

st.markdown(f'<div class="section-title">CONCLUSAO - PRODUTO {produto} - {rev.upper()}</div>',unsafe_allow_html=True)
alerts=[]
if not excess_triggers.empty:alerts.append(("warn-box","Gatilhos de excesso",f"{len(excess_triggers)} gatilho(s) identificados pelo modelo analítico de métricas, regras críticas e score."))
if int((metrics["Alerta"]=="vermelho").sum())>0:alerts.append(("alert-box","Alerta vermelho",f"{int((metrics['Alerta']=='vermelho').sum())} mês(es) acionaram regra crítica."))
if forecast_df is not None:alerts.append(("success-box","AutoETS",f"Forecast estatístico incluído para comparar PV planejado vs tendência calculada a partir do histórico até {rev}."))
if not alerts:alerts.append(("success-box","OK","Sem gatilhos críticos nos parâmetros atuais."))
for cls,t,msg in alerts:st.markdown(f'<div class="{cls}"><strong>{t}:</strong> {msg}</div>',unsafe_allow_html=True)

with st.expander("Ver dados extraídos"):
    st.dataframe(base_prod,use_container_width=True)
