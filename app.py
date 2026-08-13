from __future__ import annotations
import hmac
from pathlib import Path
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st
from src.importers import parse_alzex, load_budget, load_extraordinary
from src.storage import fetch, insert_one, insert_rows

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "initial"
st.set_page_config(page_title="Presupuesto Familiar", page_icon="💰", layout="wide")

def authenticate():
    expected = st.secrets.get("APP_PASSWORD", "")
    if not expected:
        st.error("Falta configurar APP_PASSWORD en los secretos de la aplicación.")
        st.stop()
    if st.session_state.get("authenticated"): return
    st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.title("Presupuesto Familiar")
        st.caption("Acceso privado e independiente")
        with st.form("login"):
            pwd = st.text_input("Contraseña", type="password")
            sent = st.form_submit_button("Entrar", use_container_width=True, type="primary")
        if sent:
            if hmac.compare_digest(pwd, expected):
                st.session_state.authenticated = True; st.rerun()
            st.error("Contraseña incorrecta")
    st.stop()

@st.cache_data
def initial_budget(): return load_budget(str(DATA / "ppto_2026_morus.xlsx"))
@st.cache_data
def initial_extra(): return load_extraordinary(str(DATA / "gastos_no_programados.xlsx"))
@st.cache_data
def initial_movements():
    p=DATA/"alzex_julio_2026.csv"
    return parse_alzex(p.read_bytes(),p.name)

def money(v): return f"${v:,.0f}"
def movement_data():
    rows=fetch("movements")
    df=pd.DataFrame(rows) if rows else initial_movements()
    if not df.empty:
        df["movement_date"]=pd.to_datetime(df["movement_date"]);df["amount"]=pd.to_numeric(df["amount"])
    return df

authenticate()
with st.sidebar:
    st.title("PF")
    page=st.radio("Navegación",["Resumen","Tendencias","Presupuesto","Extraordinarios","Inversiones","Importar Alzex"],label_visibility="collapsed")
    st.divider();st.caption("🔒 Datos privados")
    if st.button("Cerrar sesión",use_container_width=True):st.session_state.clear();st.rerun()

mov=movement_data();budget=initial_budget();extra=initial_extra()
monthly_budget=float(budget.monthly_budget.sum())

if page=="Resumen":
    st.title("Resumen financiero")
    st.caption("Dónde estás parado, qué se está desviando y dónde hay fugas")
    year=st.selectbox("Año",sorted(mov.movement_date.dt.year.unique(),reverse=True) if not mov.empty else [2026])
    view=mov[mov.movement_date.dt.year==year].copy() if not mov.empty else mov
    spent=float(view.amount.sum()) if not view.empty else 0
    months=max(1,view.movement_date.dt.month.nunique()) if not view.empty else 1
    target=monthly_budget*months
    delta=spent-target
    a,b,c,d=st.columns(4)
    a.metric("Gasto registrado",money(spent),f"{money(delta)} vs presupuesto")
    b.metric("Presupuesto mensual",money(monthly_budget))
    c.metric("Extraordinarios",money(float(extra.amount.sum())))
    d.metric("Promedio mensual",money(spent/months))
    if delta>0:st.warning(f"El gasto registrado está {money(delta)} arriba del objetivo acumulado para los meses disponibles.")
    else:st.success(f"El gasto registrado está {money(abs(delta))} debajo del objetivo acumulado.")
    left,right=st.columns([1.4,1])
    with left:
        if not view.empty:
            monthly=view.assign(month=view.movement_date.dt.to_period('M').astype(str)).groupby('month',as_index=False).amount.sum()
            fig=px.bar(monthly,x="month",y="amount",title="Evolución mensual",labels={"month":"Mes","amount":"Gasto"},color_discrete_sequence=["#4B806E"])
            fig.add_hline(y=monthly_budget,line_dash="dash",line_color="#C18A3B",annotation_text="Presupuesto")
            st.plotly_chart(fig,use_container_width=True)
    with right:
        if not view.empty:
            cat=view.groupby("category",as_index=False).amount.sum().nlargest(8,"amount")
            st.plotly_chart(px.bar(cat.sort_values("amount"),x="amount",y="category",orientation="h",title="Principales categorías",color_discrete_sequence=["#A85D4A"]),use_container_width=True)

elif page=="Tendencias":
    st.title("Tendencias y fugas")
    if mov.empty:st.info("Carga movimientos para analizar tendencias.")
    else:
        start,end=st.date_input("Periodo",(mov.movement_date.min().date(),mov.movement_date.max().date()))
        f=mov[(mov.movement_date.dt.date>=start)&(mov.movement_date.dt.date<=end)].copy()
        monthly=f.assign(month=f.movement_date.dt.to_period('M').dt.to_timestamp()).groupby(['month','category'],as_index=False).amount.sum()
        totals=monthly.groupby('month',as_index=False).amount.sum();totals['media_3m']=totals.amount.rolling(3,min_periods=1).mean()
        fig=px.line(totals,x='month',y=['amount','media_3m'],markers=True,title='Gasto mensual y promedio móvil de 3 meses')
        st.plotly_chart(fig,use_container_width=True)
        curr=f.groupby('category').amount.sum();rank=curr.sort_values(ascending=False).head(10).rename('gasto').reset_index()
        st.dataframe(rank,use_container_width=True,hide_index=True,column_config={'gasto':st.column_config.NumberColumn(format='$%,.0f')})

elif page=="Presupuesto":
    st.title("Presupuesto contra gasto real")
    months=st.slider("Meses a comparar",1,12,6)
    actual=mov.groupby('category').amount.sum() if not mov.empty else pd.Series(dtype=float)
    plan=budget.groupby('category').monthly_budget.sum()*months
    comp=pd.concat([plan.rename('presupuesto'),actual.rename('real')],axis=1).fillna(0);comp['variación']=comp.real-comp.presupuesto;comp['ejercicio']=comp.real/comp.presupuesto.replace(0,pd.NA)
    st.dataframe(comp.reset_index().sort_values('variación',ascending=False),use_container_width=True,hide_index=True,column_config={'presupuesto':st.column_config.NumberColumn(format='$%,.0f'),'real':st.column_config.NumberColumn(format='$%,.0f'),'variación':st.column_config.NumberColumn(format='$%,.0f'),'ejercicio':st.column_config.ProgressColumn(format='%.0f%%',min_value=0,max_value=2)})

elif page=="Extraordinarios":
    st.title("Gastos extraordinarios")
    st.metric("Total registrado",money(float(extra.amount.sum())))
    st.dataframe(extra,use_container_width=True,hide_index=True,column_config={'amount':st.column_config.NumberColumn('Importe',format='$%,.0f')})

elif page=="Inversiones":
    st.title("Inversiones y rendimientos")
    investments=pd.DataFrame(fetch('investments'))
    if not investments.empty:
        investments['balance']=pd.to_numeric(investments.balance);st.metric('Patrimonio invertido',money(investments.balance.sum()));st.dataframe(investments,use_container_width=True,hide_index=True)
    with st.expander("Agregar inversión",expanded=investments.empty):
        with st.form('investment'):
            c1,c2=st.columns(2);institution=c1.text_input('Institución');product=c2.text_input('Producto');owner=c1.text_input('Titular');asset=c2.selectbox('Tipo de activo',['Efectivo','Deuda','Renta variable','Fondo','Inmueble','Otro']);balance=c1.number_input('Saldo actual',min_value=0.0);rate=c2.number_input('Tasa anual %',min_value=0.0);maturity=st.date_input('Vencimiento',value=None);sent=st.form_submit_button('Guardar',type='primary')
        if sent:
            try:insert_one('investments',{'institution':institution,'product':product,'owner':owner,'asset_type':asset,'balance':balance,'annual_rate':rate,'maturity_date':maturity.isoformat() if maturity else None});st.success('Inversión guardada');st.rerun()
            except Exception as e:st.error(str(e))

else:
    st.title("Importar movimientos de Alzex")
    st.write("Carga un CSV completo o mensual. La huella de cada movimiento evita duplicados.")
    uploaded=st.file_uploader("Archivo CSV",type=['csv'])
    if uploaded:
        try:
            parsed=parse_alzex(uploaded.getvalue(),uploaded.name);existing={r['fingerprint'] for r in fetch('movements')};new=parsed[~parsed.fingerprint.isin(existing)]
            c1,c2,c3=st.columns(3);c1.metric('Movimientos válidos',len(parsed));c2.metric('Nuevos',len(new));c3.metric('Duplicados',len(parsed)-len(new));st.dataframe(new.head(50),use_container_width=True,hide_index=True)
            if st.button('Confirmar importación',type='primary',disabled=new.empty):
                rows=new.where(pd.notna(new),None).to_dict('records');insert_rows('movements',rows);insert_one('imports',{'file_name':uploaded.name,'row_count':len(parsed),'new_rows':len(new),'duplicate_rows':len(parsed)-len(new)});st.success('Importación completada');st.cache_data.clear();st.rerun()
        except Exception as e:st.error(f"No se pudo leer el archivo: {e}")
