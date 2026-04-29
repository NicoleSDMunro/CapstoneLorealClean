import re
import html
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Smart Launch | Supply Chain", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&display=swap');
html,body,[class*="css"]{font-family:'Helvetica Neue',Helvetica,Arial,sans-serif}.stApp{background:#000;color:#f5f5f5}.block-container{padding-top:.25rem;max-width:1188px}[data-testid="stHeader"]{background:transparent}#MainMenu,footer{visibility:hidden}.hero-title{font-family:'Barlow Condensed','Helvetica Neue',Helvetica,Arial,sans-serif;font-size:34px;line-height:1;font-weight:700;letter-spacing:.04em;text-transform:uppercase;margin-bottom:10px;color:#fff;white-space:nowrap;overflow:hidden}.hero-subtitle{color:#9ca3af;font-size:13px;font-weight:300;margin-bottom:30px}.empty-panel{background:#101010;border:1px dashed #3a3a3a;border-radius:10px;padding:34px 28px;margin-top:22px}.empty-title{font-size:24px;font-weight:850;margin-bottom:8px}.empty-text{color:#a5a5a5;font-size:15px;line-height:1.6}.stSelectbox label{color:#60646f!important;text-transform:uppercase;letter-spacing:.08em;font-size:11px!important;font-weight:400}.stSelectbox [data-baseweb="select"]>div{background:#151515!important;border:1px solid #333!important;border-radius:6px!important;color:#e5e7eb!important;min-height:42px}.stSelectbox [data-baseweb="select"] span{color:#e5e7eb!important;font-size:14px!important;font-weight:400}.info-card{height:96px;background:#111;border:.5px solid #2a2a2a;border-radius:6px;box-sizing:border-box;padding:16px 18px;display:flex;flex-direction:column;justify-content:center}.info-label{color:#555;font-size:10px;font-weight:400;letter-spacing:.07em;text-transform:uppercase;line-height:1;margin-bottom:12px}.info-value{font-size:18px;font-weight:600;line-height:1.05;white-space:nowrap}.info-sub{color:#999;font-size:11px;font-weight:400;line-height:1.2;margin-top:9px;white-space:nowrap}.orange{color:#e8a24a}.red{color:#f05a5f}.green{color:#1ca37e}.tab-single{margin:34px 0 22px}.tab-single span{display:inline-block;padding:0 26px 14px;text-transform:uppercase;letter-spacing:.07em;font-size:13px;font-weight:600;color:#fff;border-bottom:4px solid #fff}.review-title{font-size:16px;font-weight:600;letter-spacing:.02em;margin:10px 0 18px}.month-row div[data-testid="stButton"] button,[data-testid="stButton"] button[kind="secondary"]{height:42px!important;border-radius:8px!important;border:1px solid #333!important;background:#171717!important;color:#d1d5db!important;font-size:13px!important;font-weight:300!important;box-shadow:none!important}.month-row div[data-testid="stButton"] button p,[data-testid="stButton"] button[kind="secondary"] p{color:#d1d5db!important;font-size:13px!important;font-weight:300!important}.month-row div[data-testid="stButton"] button:hover,[data-testid="stButton"] button[kind="secondary"]:hover{background:#222!important;border-color:#454545!important;color:#fff!important}.month-row div[data-testid="stButton"] button[kind="primary"]{background:var(--accent)!important;color:#fff!important;border-color:var(--accent)!important;font-weight:700!important}.month-row div[data-testid="stButton"] button[kind="primary"] p{color:#fff!important;font-weight:700!important}.section-title{color:#9a9a9a;text-transform:uppercase;letter-spacing:.08em;font-size:12px;font-weight:400;margin:24px 0 10px}.chart-card{background:#101010;border:1px solid #2a2a2a;border-radius:8px;padding:8px 12px 2px}.alert-box,.warn-box,.success-box{border-radius:8px;padding:16px 20px;color:#fff;font-size:13px;font-weight:400;line-height:1.6;margin-bottom:10px}.alert-box{background:linear-gradient(90deg,rgba(239,68,68,.22),rgba(239,68,68,.05));border-left:6px solid #ef4444}.warn-box{background:linear-gradient(90deg,rgba(250,204,21,.18),rgba(250,204,21,.04));border-left:6px solid #facc15}.success-box{background:linear-gradient(90deg,rgba(22,163,123,.20),rgba(22,163,123,.04));border-left:6px solid #16a37b}.trigger-pills{display:flex;flex-wrap:wrap;gap:14px;margin:12px 0 16px}.trigger-pill-red{border:1px solid #ef4444;color:#ef4444;border-radius:999px;padding:9px 15px;font-size:13px}.trigger-pill-orange{border:1px solid #f97316;color:#f97316;border-radius:999px;padding:9px 15px;font-size:13px}.trigger-pill-yellow{border:1px solid #d49100;color:#d49100;border-radius:999px;padding:9px 15px;font-size:13px}.decision-table-wrap{background:#101010;border:1px solid #2a2a2a;border-radius:10px;padding:14px;margin:10px 0 16px}.decision-note{color:#9ca3af;font-size:13px;line-height:1.5;margin:0 0 10px}.decision-summary{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0 12px}.decision-chip{border:1px solid #303030;border-radius:999px;padding:8px 13px;color:#d1d5db;background:#0b0b0b;font-size:12px}.decision-table{width:100%;border-collapse:separate;border-spacing:0;overflow:hidden;border-radius:8px;border:1px solid #2a2a2a;background:#111}.decision-table th{background:#1a1a1a;color:#9ca3af;text-align:left;padding:12px 10px;font-size:11px;font-weight:500;text-transform:uppercase;border-bottom:1px solid #2a2a2a}.decision-table td{background:#111;color:#d1d5db;padding:12px 10px;font-size:11px;font-weight:400;border-bottom:1px solid #242424;vertical-align:top}.decision-table tr:last-child td{border-bottom:0}.decision-table tr.green td{background:rgba(34,197,94,.10)}.decision-table tr.yellow td{background:rgba(250,204,21,.11)}.decision-table tr.red td{background:rgba(239,68,68,.13)}.decision-table td:first-child{font-weight:700;color:#f5f5f5}.decision-table .status{font-weight:800;color:#f5f5f5;white-space:nowrap}
</style>
""", unsafe_allow_html=True)

MESES=["jun/25","jul/25","ago/25","set/25","out/25","nov/25","dez/25","jan/26","fev/26","mar/26","abr/26","mai/26","jun/26"]
REVISOES=MESES[:9]
PRODUTOS=list("ABCDEFGHIJKLMNOP")
MONTH_MAP={"jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,"jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12}

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
                if pd.notna(val):out.append({"Produto":product,"Variavel":var,"Revisao":period_label(revp),"Mes":period_label(tp),"Valor":float(val),"RealizadoProxy":revp==tp})
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

def generate_excess_triggers(pivot,prev,cobertura_target):
    base=pivot.set_index("Mes");prev_base=prev if prev is not None else None;rows=[]
    if "PV" not in base.columns:return pd.DataFrame(rows)
    for mes in MESES:
        if mes not in base.index:continue
        pv_atual=base.at[mes,"PV"] if "PV" in base.columns else np.nan;prod=base.at[mes,"Producao"] if "Producao" in base.columns else np.nan;estoque=base.at[mes,"Estoque"] if "Estoque" in base.columns else np.nan
        pv_anterior=prev_base.at[mes,"PV"] if prev_base is not None and "PV" in prev_base.columns and mes in prev_base.index else np.nan
        if pd.isna(pv_atual) or pd.isna(pv_anterior) or pv_anterior==0:continue
        desvio_pv=(pv_atual-pv_anterior)/pv_anterior;producao_acima_pv=pd.notna(prod) and prod>pv_atual
        cobertura_dias=(estoque/(pv_atual/30)) if pd.notna(estoque) and pv_atual else np.nan
        cobertura_vs_target=cobertura_dias/cobertura_target if pd.notna(cobertura_dias) and cobertura_target else np.nan
        if desvio_pv<-0.25 and pd.notna(cobertura_vs_target) and cobertura_vs_target>1.25 and producao_acima_pv:
            tipo,nivel,cor="Excesso severo","vermelho","#ef4444";detalhe=f"PV {abs(desvio_pv)*100:.1f}% abaixo da revisão anterior, produção acima do PV e cobertura {cobertura_vs_target*100:.0f}% do target."
        elif desvio_pv<-0.10 and pd.notna(cobertura_vs_target) and cobertura_vs_target>1:
            tipo,nivel,cor="Excesso relevante","laranja","#f97316";detalhe=f"PV {abs(desvio_pv)*100:.1f}% abaixo da revisão anterior e cobertura {cobertura_vs_target*100:.0f}% do target."
        elif desvio_pv<0 and producao_acima_pv:
            tipo,nivel,cor="Excesso em formação","amarelo","#d49100";detalhe=f"PV {abs(desvio_pv)*100:.1f}% abaixo da revisão anterior, mas produção ficou maior que o PV planejado."
        else:continue
        rows.append({"Mês":mes,"Tipo":tipo,"Nível":nivel,"Cor":cor,"Detalhe":detalhe,"PV":pv_atual,"Produção":prod,"Estoque":estoque})
    return pd.DataFrame(rows)

def calculate_decision_window(trigger_row,revisao_mes,hb_dias,lt_sem,po_emitido="Não",po_status="Aberto"):
    rev_period=mes_to_period(revisao_mes);trigger_period=mes_to_period(trigger_row["Mês"])
    hb_dias=float(pd.to_numeric(hb_dias,errors="coerce") if pd.notna(hb_dias) else 60);lt_dias=float(pd.to_numeric(lt_sem,errors="coerce") if pd.notna(lt_sem) else 16)*7
    dias_ate=max(0,int((trigger_period-rev_period).n*30)) if rev_period and trigger_period else 0
    dentro_hb=dias_ate<=hb_dias;dentro_lt=dias_ate<=lt_dias;entrando_lt=lt_dias<dias_ate<=lt_dias+30;po_confirmado=po_emitido=="Sim" and po_status in ["Em produção","Em trânsito"]
    if dentro_hb or dentro_lt or po_confirmado: estado,emoji,classe,texto="EXCESSO COMPROMETIDO","🔴","red","Comprometido: compras/produção já estão travadas por HB, LT ou PO confirmado."
    elif entrando_lt: estado,emoji,classe,texto="ÚLTIMA JANELA","🟡","yellow","Ainda dá para agir, mas está entrando no LT. A decisão é possível com risco."
    else: estado,emoji,classe,texto="AÇÃO POSSÍVEL","🟢","green","Ainda dá para agir: o gatilho está fora do HB e fora do LT."
    hb_txt=f"Dentro ({dias_ate}d ≤ {hb_dias:.0f}d)" if dentro_hb else f"Fora ({dias_ate}d > {hb_dias:.0f}d)"
    lt_txt=f"Dentro ({dias_ate}d ≤ {lt_dias:.0f}d)" if dentro_lt else (f"Última janela ({dias_ate}d; LT {lt_dias:.0f}d + 30d)" if entrando_lt else f"Fora ({dias_ate}d > {lt_dias+30:.0f}d)")
    po_txt=f"Sim — {po_status}" if po_emitido=="Sim" else "Não informado/Não emitido"
    return {"Mês do gatilho":trigger_row["Mês"],"Status decisão":f"{emoji} {estado}","HB":hb_txt,"LT":lt_txt,"PO":po_txt,"Interpretação":texto,"Classe":classe}

def fmt(v):
    v=float(v)
    if abs(v)>=1_000_000:return f"{v/1_000_000:.1f}M"
    if abs(v)>=1000:return f"{v:,.0f}".replace(",",".")
    return f"{v:.0f}"

def cor_revisao(rev):
    if str(rev).startswith("jun"):return "#5b9cff"
    if str(rev).startswith("jul"):return "#16a37b"
    if str(rev).startswith("ago"):return "#e5533f"
    return "#f4474c"

def info_card(label,value,sub,cls):
    st.markdown(f'<div class="info-card"><div class="info-label">{html.escape(str(label))}</div><div class="info-value {cls}">{html.escape(str(value))}</div><div class="info-sub">{html.escape(str(sub))}</div></div>',unsafe_allow_html=True)

def render_decision_table(df):
    cols=["Mês do gatilho","Status decisão","HB","LT","PO","Interpretação"]
    head="".join([f"<th>{html.escape(c)}</th>" for c in cols]);rows=""
    for _,r in df.iterrows():rows+=f"<tr class='{html.escape(r['Classe'])}'>"+"".join([f"<td class='{'status' if c=='Status decisão' else ''}'>{html.escape(str(r[c]))}</td>" for c in cols])+"</tr>"
    st.markdown(f"<table class='decision-table'><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>",unsafe_allow_html=True)

with st.sidebar:
    st.header("Base de dados");arquivo=st.file_uploader("Suba sua base Excel",type=["xlsx"]);st.caption("O arquivo pode ter qualquer nome, desde que respeite o formato: abas Base, BOM e produtos A–P.")

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
scols=st.columns(5,gap="small");items=[("ORIGEM",info["Origem"],"","orange"),("LT MAX",f"{lt_sem:.0f} sem",f"aprox {lt_meses:.1f}m - {lt_dias}d",lt_cls),("COB. TARGET",f"{ct_dias:.0f}d",f"aprox {ct_dias/30:.1f}m - {ct_dias/7:.1f}sem",ct_cls),("DEMANDA",info["Demanda"],"",dem_cls),("EST. FINAL",fmt(est_final),"última rev - jun/26",est_cls)]
for i,(lab,val,sub,cls) in enumerate(items):
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
prev_idx=revisoes.index(rev)-1
if prev_idx>=0:
    prev=base_prod[base_prod["Revisao"]==revisoes[prev_idx]].pivot_table(index="Mes",columns="Variavel",values="Valor",aggfunc="sum").reindex(MESES);var_pv=(pivot.set_index("Mes")["PV"]-prev["PV"])/prev["PV"].replace(0,np.nan);meses_acima=int((var_pv.abs()>.10).sum())
else:prev=None;meses_acima=0
excess_triggers=generate_excess_triggers(pivot,prev,ct_dias)
if not excess_triggers.empty:
    red_count=int((excess_triggers["Nível"]=="vermelho").sum());orange_count=int((excess_triggers["Nível"]=="laranja").sum());yellow_count=int((excess_triggers["Nível"]=="amarelo").sum())
    st.markdown(f'<div class="trigger-pills"><span class="trigger-pill-red">🔴 Excesso severo&nbsp; <strong>{red_count}</strong></span><span class="trigger-pill-orange">🟠 Excesso relevante&nbsp; <strong>{orange_count}</strong></span><span class="trigger-pill-yellow">🟡 Em formação&nbsp; <strong>{yellow_count}</strong></span></div>',unsafe_allow_html=True)
st.markdown(f'<div class="section-title">PV - PRODUCAO - ESTOQUE - {rev.upper()}</div>',unsafe_allow_html=True);st.markdown('<div class="chart-card">',unsafe_allow_html=True)
fig=go.Figure()
for var,color,dash,name in [("PV","#5b9cff","solid","PV (Sell In)"),("Producao","#45c49b","dash","Producao"),("Estoque","#e7895e","dot","Estoque")]:
    if var in pivot:fig.add_trace(go.Scatter(x=pivot["Mes"],y=pivot[var],mode="lines+markers",name=name,line=dict(width=3,color=color,dash=dash),marker=dict(size=7),hovertemplate=f"{name}: %{{y:,.0f}}<extra></extra>"))
if rev in MESES:fig.add_vline(x=rev,line_width=1.5,line_dash="dash",line_color="#6b7280")
if not excess_triggers.empty:
    for _,row in excess_triggers.iterrows():fig.add_vline(x=row["Mês"],line_width=1.5,line_dash="dash",line_color=row["Cor"])
    fig.add_trace(go.Scatter(x=excess_triggers["Mês"],y=excess_triggers["PV"],mode="markers",name="Gatilhos de excesso",marker=dict(size=17,color="rgba(0,0,0,0)",line=dict(color=excess_triggers["Cor"],width=4),symbol="circle"),customdata=np.stack([excess_triggers["Tipo"],excess_triggers["Detalhe"]],axis=-1),hovertemplate="%{customdata[0]}<br>%{customdata[1]}<extra></extra>"))
fig.update_layout(paper_bgcolor="#101010",plot_bgcolor="#101010",font=dict(family="Helvetica Neue, Helvetica, Arial, sans-serif",color="#999",size=11),height=430,margin=dict(l=30,r=18,t=18,b=35),legend=dict(orientation="h",y=-.22,x=.20,font=dict(size=12,color="#999")),xaxis=dict(gridcolor="#202020",zerolinecolor="#202020"),yaxis=dict(gridcolor="#202020",zerolinecolor="#202020"),hovermode="x unified",hoverlabel=dict(bgcolor="#171717",bordercolor="#2a2a2a",font=dict(color="#f5f5f5",size=12)))
st.plotly_chart(fig,use_container_width=True);st.markdown('</div>',unsafe_allow_html=True)
if not excess_triggers.empty:
    st.markdown('<div class="section-title">BLOCO 2 — JANELA DE DECISAO</div>',unsafe_allow_html=True)
    st.markdown('<div class="decision-table-wrap"><p class="decision-note">A Janela de Decisão não cria novos alertas. Ela resume, em tabela, se ainda existe viabilidade de ação para cada gatilho já detectado.</p>',unsafe_allow_html=True)
    with st.expander("Inputs opcionais de PO",expanded=False):
        po_emitido=st.selectbox("PO já emitido?",["Não","Sim"],index=0);po_status=st.selectbox("Status do PO",["Aberto","Em produção","Em trânsito"],index=0)
    decision_df=pd.DataFrame([calculate_decision_window(row,rev,hb_dias,lt_sem,po_emitido,po_status) for _,row in excess_triggers.iterrows()]);counts=decision_df["Status decisão"].str.replace("🟢 ","",regex=False).str.replace("🟡 ","",regex=False).str.replace("🔴 ","",regex=False).value_counts().to_dict()
    st.markdown(f'<div class="decision-summary"><span class="decision-chip">🟢 Ação possível: {counts.get("AÇÃO POSSÍVEL",0)}</span><span class="decision-chip">🟡 Última janela: {counts.get("ÚLTIMA JANELA",0)}</span><span class="decision-chip">🔴 Comprometido: {counts.get("EXCESSO COMPROMETIDO",0)}</span></div>',unsafe_allow_html=True)
    render_decision_table(decision_df);st.markdown('</div>',unsafe_allow_html=True)
st.markdown(f'<div class="section-title">CONCLUSAO - PRODUTO {produto} - {rev.upper()}</div>',unsafe_allow_html=True)
alerts=[]
if est_final<0:alerts.append(("alert-box","Ruptura projetada","estoque final negativo em jun/26."))
if lt_dias>ct_dias:alerts.append(("alert-box","Risco estrutural",f"LT ({lt_dias}d) maior que Cobertura Target ({ct_dias:.0f}d). Demanda surpresa nao pode ser respondida a tempo."))
if meses_acima>0:alerts.append(("warn-box","Revisao instavel",f"{meses_acima} meses tiveram variacao de PV superior a 10% vs revisao anterior."))
if not excess_triggers.empty:alerts.append(("warn-box","Gatilhos de excesso",f"{len(excess_triggers)} gatilho(s) identificados automaticamente no gráfico. A Janela de Decisão em tabela mostra se ainda dá para agir."))
if not alerts:alerts.append(("success-box","OK","Forecast estavel, sem alerta critico nos parametros atuais."))
for cls,t,msg in alerts:st.markdown(f'<div class="{cls}"><strong>{t}:</strong> {msg}</div>',unsafe_allow_html=True)
st.markdown('<div class="section-title">VARIACAO VS MES ANTERIOR</div>',unsafe_allow_html=True)
if prev_idx>=0 and prev is not None:
    atual=pivot.set_index("Mes")[[c for c in ["PV","Producao","Estoque"] if c in pivot]];anterior=prev[[c for c in ["PV","Producao","Estoque"] if c in prev]];tab=((atual-anterior)/anterior.replace(0,np.nan)*100).round(1).reset_index();st.dataframe(tab,use_container_width=True)
else:st.info("Revisão base: não existe mês anterior para comparar.")
with st.expander("Ver dados extraídos"):st.dataframe(base_prod,use_container_width=True)
