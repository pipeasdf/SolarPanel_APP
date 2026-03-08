"""
Financial History Page - Solar Panel Monitoring

Detailed monthly breakdown of savings and theoretical grid bill costs.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path
from sqlalchemy import func

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_session_context, get_setting, Record, get_settings_by_category
from src.calculations.financial import calculate_theoretical_bill

st.set_page_config(page_title="Histórico Financiero", page_icon="💰", layout="wide")

st.title("💰 Histórico Financiero")
st.markdown("---")

# Load Settings
financial_settings = get_settings_by_category('financial')
cost_kwh = float(financial_settings.get('cost_kwh', '235.45'))
usd_rate = float(financial_settings.get('usd_clp_rate', '950'))

# --- Data Loading ---
def load_monthly_data():
    with get_session_context() as session:
        # Group by Year-Month
        # SQLite uses strftime slightly differently than Postgres, but SQLAlchemy helps abstraction
        # For simplicity in pure Python with SQLite datetime strings:
        records = session.query(Record).all()
        
        if not records:
            return pd.DataFrame()
            
        data = []
        for r in records:
            data.append({
                'date': r.timestamp,
                'year': r.timestamp.year,
                'month': r.timestamp.month,
                'yield_wh': r.yield_wh
            })
            
        df = pd.DataFrame(data)
        if df.empty:
            return df
            
        # Group by Year, Month
        monthly = df.groupby(['year', 'month']).agg({
            'yield_wh': 'sum'
        }).reset_index()
        
        # Add Date column for plotting (first day of month)
        monthly['date_str'] = monthly.apply(lambda x: f"{int(x['year'])}-{int(x['month']):02d}", axis=1)
        monthly['date_dt'] = pd.to_datetime(monthly['date_str'])
        
        # Calculate Financials
        monthly['yield_kwh'] = monthly['yield_wh'] / 1000.0
        
        # Savings (Variable only: Energy * Price)
        monthly['savings_clp'] = monthly['yield_kwh'] * cost_kwh
        monthly['savings_usd'] = monthly['savings_clp'] / usd_rate
        
        # Theoretical Bill (What I would have paid)
        # Assuming the 'yield_kwh' was consumed. 
        # Theoretical Bill = (Yield * Cost) + Fixed Costs
        monthly['theoretical_bill_clp'] = monthly['yield_kwh'].apply(
            lambda kwh: calculate_theoretical_bill(kwh, financial_settings)
        )
        
        # Net Benefit (Total Saved = Theoretical Bill if we assume we went 100% solar that month)
        # Note: True savings depend: are we Off-Grid? 
        # If Off-Grid: We save the ENTIRE Bill (Fixed + Variable).
        # If Grid-Tied (Net Billing): We save mostly Variable.
        # Let's assume Off-Grid/Hybrid where we produce our own power.
        # But to be conservative in the "Savings" column we usually track Generation Value.
        # Let's add a "Total Avoided Cost" column which includes fixed costs.
        monthly['avoided_cost_clp'] = monthly['theoretical_bill_clp']
        
        return monthly.sort_values('date_dt', ascending=False)

df_monthly = load_monthly_data()

if df_monthly.empty:
    st.warning("No hay datos históricos suficientes para mostrar el análisis.")
    st.stop()

# --- Filters ---
col_filter, _ = st.columns([1, 3])
with col_filter:
    years = sorted(df_monthly['year'].unique(), reverse=True)
    selected_year = st.selectbox("Seleccionar Año", options=["Todos"] + list(years))

if selected_year != "Todos":
    df_view = df_monthly[df_monthly['year'] == selected_year]
else:
    df_view = df_monthly

# --- Summary Metrics ---
st.subheader("Resumen del Período")
total_gen = df_view['yield_kwh'].sum()
total_saved = df_view['savings_clp'].sum()
total_avoided = df_view['avoided_cost_clp'].sum()

m1, m2, m3 = st.columns(3)
m1.metric("Energía Total Generada", f"{total_gen:,.1f} kWh")
m2.metric("Ahorro por Energía (CLP)", f"${total_saved:,.0f}")
m3.metric("Costo de Red Evitado (Est.)", f"${total_avoided:,.0f}", help="Incluye cargos fijos teóricos")

st.markdown("---")

# --- Charts ---
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    fig_bar = px.bar(
        df_view,
        x='date_str',
        y='savings_clp',
        title='Ahorro Mensual ( Solo Energía )',
        labels={'date_str': 'Mes', 'savings_clp': 'CLP'},
        text_auto='.2s',
        color='savings_clp',
        color_continuous_scale='Greens'
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_chart2:
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Scatter(
        x=df_view['date_str'],
        y=df_view['theoretical_bill_clp'],
        mode='lines+markers',
        name='Factura Teórica (Red)',
        line=dict(color='#F44336', width=3, dash='dash')
    ))
    fig_comp.add_trace(go.Bar(
        x=df_view['date_str'],
        y=df_view['savings_clp'],
        name='Generación Solar',
        marker_color='#4CAF50'
    ))
    fig_comp.update_layout(
        title="Comparativa: Solar vs Red",
        xaxis_title="Mes",
        yaxis_title="Costo (CLP)",
        legend=dict(orientation='h', y=1.1)
    )
    st.plotly_chart(fig_comp, use_container_width=True)

# --- Detailed Table ---
st.subheader("Desglose Mensual")

display_cols = ['date_str', 'yield_kwh', 'savings_clp', 'savings_usd', 'theoretical_bill_clp']
df_table = df_view[display_cols].copy()
df_table.columns = ['Mes', 'Generación (kWh)', 'Ahorro Variable (CLP)', 'Ahorro (USD)', 'Factura Evitada (CLP)']

st.dataframe(
    df_table.style.format({
        'Generación (kWh)': '{:.1f}',
        'Ahorro Variable (CLP)': '${:,.0f}',
        'Ahorro (USD)': '${:,.2f}',
        'Factura Evitada (CLP)': '${:,.0f}'
    }),
    use_container_width=True
)
