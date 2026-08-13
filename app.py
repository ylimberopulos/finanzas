from pathlib import Path
import hmac, pandas as pd, plotly.express as px, plotly.graph_objects as go, streamlit as st
from src.importers import parse_alzex,load_budget,load_extraordinary,load_compiled_monthly
from src.storage import fetch,insert_one,insert_rows
ROOT=Path(__file__).parent;DATA=ROOT/'data'/'initial';MONTHS={1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'};NAVY='#172A46';BLUE='#2563EB';SKY='#60A5FA';GOLD='#D59A33';GRID='#E5EAF1'
st.set_page_config(page_title='Presupuesto Familiar',page_icon='💰',layout='wide')
st.markdown("""<style>.stApp{background:#F7F9FC}.block-container{padding-top:2rem;max-width:1500px}h1,h2,h3{color:#172A46!important}.stMetric{background:white;border:1px solid #E5EAF1;border-radius:14px;padding:16px;box-shadow:0 2px 8px #172A4610}[data-testid='stSidebar']{background:#172A46}[data-testid='stSidebar'] *{color:#F8FAFC!important}.stDataFrame{border:1px solid #E5EAF1;border-radius:12px;overflow:hidden}</style>""",unsafe_allow_html=True)
def authenticate():
    expected=st.secrets.get('APP_PASSWORD','')
    if not expected:st.error('Falta configurar APP_PASSWORD.');st.stop()
    if st.session_state.get('authenticated'):return
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown('<div style="height:12vh"></div>',unsafe_allow_html=True);st.title('Presupuesto Familiar')
        with st.form('login'):pwd=st.text_input('Contraseña',type='password');sent=st.form_submit_button('Entrar',use_container_width=True,type='primary')
        if sent:
            if hmac.compare_digest(pwd,expected):st.session_state.authenticated=True;st.rerun()
            st.error('Contraseña incorrecta')
    st.stop()
@st.cache_data
def budget_data():return load_budget(str(DATA/'ppto_2026_morus.xlsx'))
@st.cache_data
def extraordinary_data():return load_extraordinary(str(DATA/'gastos_no_programados.xlsx'))
@st.cache_data
def initial_movements():
    p=DATA/'alzex_julio_2026.csv';return parse_alzex(p.read_bytes(),p.name)
@st.cache_data
def compiled_data():return load_compiled_monthly(str(DATA/'2026_ene_jul.xlsx'))
def money(v):return f'${v:,.2f}' if abs(v-round(v))>.001 else f'${v:,.0f}'
def style(fig):
    fig.update_layout(font=dict(color=NAVY),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',margin=dict(l=10,r=10,t=52,b=10),legend_title_text='');fig.update_xaxes(gridcolor=GRID);fig.update_yaxes(gridcolor=GRID);return fig
def db_movements():
    rows=fetch('movements');df=pd.DataFrame(rows) if rows else initial_movements()
    if not df.empty:df['movement_date']=pd.to_datetime(df.movement_date);df['amount']=pd.to_numeric(df.amount)
    return df
def analytical_monthly():
    base=compiled_data().copy();mov=db_movements()
    if not mov.empty:
        tx=mov.assign(year=mov.movement_date.dt.year,month=mov.movement_date.dt.month,month_name=mov.movement_date.dt.month.map(MONTHS)).groupby(['year','month','month_name','category'],as_index=False).amount.sum();tx['source']='Alzex';keys=set(zip(tx.year,tx.month));base=base[~base[['year','month']].apply(tuple,axis=1).isin(keys)];base=pd.concat([base,tx],ignore_index=True)
    return base
def period_filter(df,key):
    years=sorted(df.year.unique(),reverse=True);c1,c2,c3=st.columns([1,1,1.4]);year=c1.selectbox('Año',years,key='y'+key);available=sorted(df.loc[df.year==year,'month'].unique());options=['Acumulado']+[MONTHS[m] for m in available];choice=c2.selectbox('Vista',options,index=len(options)-1,key='m'+key)
    if choice=='Acumulado':end=c3.selectbox('Acumulado hasta',[MONTHS[m] for m in available],index=len(available)-1,key='e'+key);end_month={v:k for k,v in MONTHS.items()}[end];selected=list(range(1,end_month+1));label=f'Enero–{end} {year}'
    else:selected=[{v:k for k,v in MONTHS.items()}[choice]];label=f'{choice} {year}'
    return df[(df.year==year)&(df.month.isin(selected))].copy(),selected,label
authenticate()
with st.sidebar:
    st.markdown('## 💰 Presupuesto');page=st.radio('Navegación',['Resumen','Tendencias y fugas','Presupuesto','Extraordinarios','Inversiones','Importar Alzex'],label_visibility='collapsed');st.divider();st.caption('🔒 Datos privados')
    if st.button('Cerrar sesión',use_container_width=True):st.session_state.clear();st.rerun()
monthly=analytical_monthly();budget=budget_data();extra=extraordinary_data();monthly_budget=float(budget.monthly_budget.sum())
if page=='Resumen':
    st.title('Resumen financiero');st.caption('Dónde estás parado, qué se está desviando y dónde hay fugas');view,selected,label=period_filter(monthly,'sum');spent=float(view.amount.sum());target=monthly_budget*len(selected);delta=spent-target;st.markdown('#### '+label);a,b,c,d=st.columns(4);a.metric('Gasto registrado',money(spent),f'{money(delta)} vs. presupuesto');b.metric('Presupuesto del periodo',money(target));c.metric('Extraordinarios registrados',money(float(extra.amount.sum())));d.metric('Promedio mensual',money(spent/max(1,len(selected))));(st.warning if delta>0 else st.success)(f"El gasto está {money(abs(delta))} {'arriba' if delta>0 else 'debajo'} del presupuesto.")
    left,right=st.columns([1.35,1])
    with left:
        trend=view.groupby(['month','month_name'],as_index=False).amount.sum().sort_values('month');fig=px.bar(trend,x='month_name',y='amount',title='Gasto mensual',text_auto=',.0f',color_discrete_sequence=[BLUE],labels={'month_name':'Mes','amount':'Gasto'});fig.add_hline(y=monthly_budget,line_dash='dash',line_color=GOLD,annotation_text=f'Presupuesto {money(monthly_budget)}');fig.update_yaxes(tickprefix='$',tickformat=',.0f');st.plotly_chart(style(fig),use_container_width=True)
    with right:
        cat=view.groupby('category',as_index=False).amount.sum().nlargest(10,'amount');fig=px.bar(cat.sort_values('amount'),x='amount',y='category',orientation='h',title='Principales categorías',color_discrete_sequence=[SKY],labels={'category':'Categoría','amount':'Gasto'});fig.update_xaxes(tickprefix='$',tickformat=',.0f');st.plotly_chart(style(fig),use_container_width=True)
elif page=='Tendencias y fugas':
    st.title('Tendencias y fugas');st.caption('Evolución, concentración y categorías que más presionan el gasto');view,selected,label=period_filter(monthly,'trend');st.markdown('#### '+label);trend=view.groupby(['month','month_name'],as_index=False).amount.sum().sort_values('month');trend['media']=trend.amount.rolling(3,min_periods=1).mean();fig=go.Figure();fig.add_bar(x=trend.month_name,y=trend.amount,name='Gasto mensual',marker_color=SKY,text=[money(x) for x in trend.amount],textposition='outside');fig.add_scatter(x=trend.month_name,y=trend.media,name='Promedio móvil 3 meses',line=dict(color=NAVY,width=3),mode='lines+markers');fig.add_hline(y=monthly_budget,line_dash='dash',line_color=GOLD,annotation_text='Presupuesto mensual');fig.update_yaxes(tickprefix='$',tickformat=',.0f');fig.update_layout(title='Gasto y tendencia mensual');st.plotly_chart(style(fig),use_container_width=True);current=view.groupby('category',as_index=False).amount.sum().sort_values('amount',ascending=False);current['share']=current.amount/current.amount.sum();current.columns=['Categoría','Gasto','Participación'];st.subheader('Concentración del gasto');st.dataframe(current,hide_index=True,use_container_width=True,column_config={'Gasto':st.column_config.NumberColumn(format='dollar'),'Participación':st.column_config.ProgressColumn(format='percent',min_value=0,max_value=1)})
elif page=='Presupuesto':
    st.title('Presupuesto contra gasto real');st.caption('Comparación mensual o acumulada con categorías conciliadas');view,selected,label=period_filter(monthly,'bud');plan=budget.groupby('category').monthly_budget.sum()*len(selected);actual=view.groupby('category').amount.sum();comp=pd.concat([plan.rename('Presupuesto'),actual.rename('Real')],axis=1).fillna(0);comp['Variación']=comp.Real-comp.Presupuesto;comp['Ejercicio']=comp.Real/comp.Presupuesto.replace(0,pd.NA);comp=comp.reset_index().rename(columns={'category':'Categoría'}).sort_values('Variación',ascending=False);st.markdown('#### '+label);c1,c2,c3=st.columns(3);c1.metric('Presupuesto',money(comp.Presupuesto.sum()));c2.metric('Gasto real',money(comp.Real.sum()));c3.metric('Variación',money(comp.Variación.sum()));st.dataframe(comp,hide_index=True,use_container_width=True,column_config={'Presupuesto':st.column_config.NumberColumn(format='dollar'),'Real':st.column_config.NumberColumn(format='dollar'),'Variación':st.column_config.NumberColumn(format='dollar'),'Ejercicio':st.column_config.ProgressColumn(format='percent',min_value=0,max_value=2)})
elif page=='Extraordinarios':
    st.title('Gastos extraordinarios');st.metric('Total registrado',money(float(extra.amount.sum())));show=extra.rename(columns={'month':'Mes','concept':'Concepto','amount':'Importe'});st.dataframe(show,hide_index=True,use_container_width=True,column_config={'Importe':st.column_config.NumberColumn(format='dollar')})
elif page=='Inversiones':
    st.title('Inversiones y rendimientos');investments=pd.DataFrame(fetch('investments'))
    if not investments.empty:investments['balance']=pd.to_numeric(investments.balance);st.metric('Patrimonio invertido',money(investments.balance.sum()));st.dataframe(investments,use_container_width=True,hide_index=True)
    with st.expander('Agregar inversión',expanded=investments.empty):
        with st.form('investment'):
            c1,c2=st.columns(2);institution=c1.text_input('Institución');product=c2.text_input('Producto');owner=c1.text_input('Titular');asset=c2.selectbox('Tipo de activo',['Efectivo','Deuda','Renta variable','Fondo','Inmueble','Otro']);balance=c1.number_input('Saldo actual',min_value=0.0);rate=c2.number_input('Tasa anual %',min_value=0.0);maturity=st.date_input('Vencimiento',value=None);sent=st.form_submit_button('Guardar',type='primary')
        if sent:
            try:insert_one('investments',{'institution':institution,'product':product,'owner':owner,'asset_type':asset,'balance':balance,'annual_rate':rate,'maturity_date':maturity.isoformat() if maturity else None});st.success('Inversión guardada');st.rerun()
            except Exception as e:st.error(str(e))
else:
    st.title('Importar movimientos de Alzex');st.write('Carga un CSV completo o mensual. La huella de cada movimiento evita duplicados.');uploaded=st.file_uploader('Archivo CSV',type=['csv'])
    if uploaded:
        try:
            parsed=parse_alzex(uploaded.getvalue(),uploaded.name);existing={r['fingerprint'] for r in fetch('movements')};new=parsed[~parsed.fingerprint.isin(existing)];c1,c2,c3=st.columns(3);c1.metric('Movimientos válidos',f'{len(parsed):,}');c2.metric('Nuevos',f'{len(new):,}');c3.metric('Duplicados',f'{len(parsed)-len(new):,}');st.dataframe(new.head(50),use_container_width=True,hide_index=True)
            if st.button('Confirmar importación',type='primary',disabled=new.empty):insert_rows('movements',new.where(pd.notna(new),None).to_dict('records'));insert_one('imports',{'file_name':uploaded.name,'row_count':len(parsed),'new_rows':len(new),'duplicate_rows':len(parsed)-len(new)});st.success('Importación completada');st.cache_data.clear();st.rerun()
        except Exception as e:st.error(f'No se pudo leer el archivo: {e}')
