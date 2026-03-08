"""
Dashboard Page - Solar Panel Monitoring

Main dashboard with KPIs, interactive charts, and data tables.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_session_context, get_setting, Record, Alert, init_db
from src.calculations import (
    calculate_soc, calculate_kpis, get_daily_dataframe,
    generate_interpretation, get_voltage_reference_lines
)
from src.calculations.financial import (
    calculate_total_savings, calculate_roi_metrics, 
    calculate_monthly_savings, calculate_theoretical_bill,
    calculate_total_historical_savings
)
from src.calculations.alerts import detect_alerts, get_alert_summary, Severity
from src.database import get_settings_by_category

# Initialize database
init_db()

st.set_page_config(page_title="Dashboard - Solar Monitor", page_icon="📊", layout="wide")

st.title("📊 Dashboard")
st.markdown("---")


def load_data(days: int = 30) -> pd.DataFrame:
    """Load records from database."""
    with get_session_context() as session:
        cutoff_date = datetime.now() - timedelta(days=days)
        records = session.query(Record).filter(
            Record.timestamp >= cutoff_date
        ).order_by(Record.timestamp.desc()).all()
        
        if not records:
            return pd.DataFrame()
        
        data = [{
            'timestamp': r.timestamp,
            'yield_wh': r.yield_wh,
            'min_voltage': r.min_voltage,
            'max_voltage': r.max_voltage,
            'bulk_m': r.bulk_m,
            'absorption_m': r.absorption_m,
            'float_m': r.float_m,
            'pv_power_max': r.pv_power_max,
            'pv_voltage_max': r.pv_voltage_max,
            'error_text': r.error_text
        } for r in records]
        
        return pd.DataFrame(data)


# Sidebar filters
with st.sidebar:
    st.header("🔍 Filtros")
    
    days_filter = st.selectbox(
        "Período",
        options=[7, 14, 30, 60, 90, 180, 365],
        index=2,
        format_func=lambda x: f"Últimos {x} días"
    )
    
    st.markdown("---")
    
    # Threshold settings display
    st.header("⚡ Umbrales")
    v_full = float(get_setting('v_full_pack', '56.4'))
    v_cutoff = float(get_setting('v_cutoff', '37.5'))
    v_warning = float(get_setting('v_warning', '44.0'))
    v_critical = float(get_setting('v_critical', '42.0'))
    
    st.caption(f"V Full: {v_full}V")
    st.caption(f"V Cutoff: {v_cutoff}V")
    st.caption(f"V Warning: {v_warning}V")
    st.caption(f"V Critical: {v_critical}V")
    
    st.markdown("---")
    
    # Financial settings preview
    st.header("💰 Finanzas")
    financial_settings = get_settings_by_category('financial')
    investment = float(financial_settings.get('initial_investment', '5000000'))
    usd_rate = float(financial_settings.get('usd_clp_rate', '950'))
    
    st.caption(f"Inv. Inicial: ${investment:,.0f} CLP")
    st.caption(f"Dólar: ${usd_rate} CLP")


# Load data
df = load_data(days_filter)

if df.empty:
    st.warning("⚠️ No hay datos disponibles. Por favor, sube un archivo CSV en la página de Upload.")
    st.stop()

# Prepare data with SOC calculations
df_display = get_daily_dataframe(df, v_full, v_cutoff, v_warning)
df_display = df_display.sort_values('timestamp')

# Calculate KPIs
kpis = calculate_kpis(df, v_full, v_cutoff, v_warning, v_critical)


# KPI Cards
st.subheader("📈 Indicadores Clave")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label="Producción Total",
        value=f"{kpis.total_yield_kwh:.1f} kWh",
        help="Producción total del período"
    )

with col2:
    st.metric(
        label="Promedio Diario",
        value=f"{kpis.average_daily_yield_wh:.0f} Wh",
        help="Producción promedio por día"
    )

with col3:
    delta_color = "normal" if kpis.average_soc >= 50 else "inverse"
    st.metric(
        label="SOC Promedio",
        value=f"{kpis.average_soc:.1f}%",
        delta=f"Min: {kpis.min_soc:.0f}%",
        delta_color=delta_color,
        help="Estado de carga promedio basado en voltaje mínimo"
    )

with col4:
    pct_deep = (kpis.days_deep_discharge / kpis.total_days * 100) if kpis.total_days > 0 else 0
    st.metric(
        label="Días Descarga Profunda",
        value=f"{kpis.days_deep_discharge}",
        delta=f"{pct_deep:.1f}%",
        delta_color="inverse" if pct_deep > 20 else "normal",
        help=f"Días con voltaje < {v_warning}V"
    )

with col5:
    st.metric(
        label="Días Analizados",
        value=f"{kpis.total_days}",
        help="Total de días con datos"
    )


st.markdown("---")


# Financial Section (ROI & Savings)
st.subheader("💰 Ahorro y ROI")

# Calculate financial metrics
# We now use the database to get the ALL-TIME total, not just the filtered period
cost_per_kwh = float(financial_settings.get('cost_kwh', '235.45'))
with get_session_context() as session:
    total_savings_clp = calculate_total_historical_savings(session, financial_settings)

roi_data = calculate_roi_metrics(total_savings_clp, financial_settings)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Ahorro Total Acumulado",
        value=f"${roi_data['total_savings_clp']:,.0f} CLP",
        delta=f"{roi_data['total_savings_usd']:,.2f} USD",
        help="Ahorro estimado basado en energía generada × costo kWh"
    )

with col2:
    st.metric(
        label="Inversión Inicial",
        value=f"${roi_data['investment_clp']:,.0f} CLP",
        help="Costo inicial del sistema"
    )

with col3:
    st.metric(
        label="ROI (Retorno Inversión)",
        value=f"{roi_data['roi_percentage']:.1f}%",
        delta=roi_data['status_text'],
        delta_color="normal" if roi_data['is_recovered'] else "off",
        help="Porcentaje de la inversión recuperada mediante ahorros"
    )

with col4:
    if roi_data['is_recovered']:
        st.success("🎉 ¡Inversión Pagada!")
    else:
        st.metric(
            label="Faltante por Recuperar",
            value=f"${roi_data['remaining_clp']:,.0f} CLP",
            delta="En progreso",
            delta_color="inverse"
        )


st.markdown("---")


# Charts section
st.subheader("📊 Gráficos")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔋 Producción Diaria", 
    "⚡ Voltajes",
    "⏱️ Tiempos de Carga",
    "💰 Análisis Financiero",
    "📊 Distribución SOC"
])

with tab1:
    # Daily yield chart
    fig_yield = px.bar(
        df_display,
        x='timestamp',
        y='yield_wh',
        title='Producción Diaria (Wh)',
        labels={'timestamp': 'Fecha', 'yield_wh': 'Producción (Wh)'},
        color='yield_wh',
        color_continuous_scale='Greens'
    )
    fig_yield.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Producción (Wh)",
        showlegend=False,
        height=400
    )
    st.plotly_chart(fig_yield, use_container_width=True)

with tab2:
    # Voltage chart with reference lines
    fig_voltage = go.Figure()
    
    # Min voltage line
    fig_voltage.add_trace(go.Scatter(
        x=df_display['timestamp'],
        y=df_display['min_voltage'],
        mode='lines+markers',
        name='Voltaje Mínimo',
        line=dict(color='#2196F3', width=2),
        marker=dict(size=6)
    ))
    
    # Max voltage line
    fig_voltage.add_trace(go.Scatter(
        x=df_display['timestamp'],
        y=df_display['max_voltage'],
        mode='lines+markers',
        name='Voltaje Máximo',
        line=dict(color='#4CAF50', width=2),
        marker=dict(size=6)
    ))
    
    # Reference lines
    ref_lines = get_voltage_reference_lines(v_full, v_cutoff, v_warning, v_critical)
    
    for ref_name, ref_data in ref_lines.items():
        fig_voltage.add_hline(
            y=ref_data['value'],
            line_dash=ref_data['dash'],
            line_color=ref_data['color'],
            annotation_text=ref_data['label'],
            annotation_position="right"
        )
    
    fig_voltage.update_layout(
        title='Voltajes del Banco 48V',
        xaxis_title='Fecha',
        yaxis_title='Voltaje (V)',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        height=450,
        yaxis=dict(range=[35, 60])
    )
    st.plotly_chart(fig_voltage, use_container_width=True)

with tab3:
    # Stacked bar chart for charge times
    fig_charge = go.Figure()
    
    fig_charge.add_trace(go.Bar(
        x=df_display['timestamp'],
        y=df_display['bulk_m'],
        name='Bulk',
        marker_color='#FF9800'
    ))
    
    fig_charge.add_trace(go.Bar(
        x=df_display['timestamp'],
        y=df_display['absorption_m'],
        name='Absorción',
        marker_color='#FFC107'
    ))
    
    fig_charge.add_trace(go.Bar(
        x=df_display['timestamp'],
        y=df_display['float_m'],
        name='Flotación',
        marker_color='#4CAF50'
    ))
    
    fig_charge.update_layout(
        barmode='stack',
        title='Tiempos de Carga Diarios',
        xaxis_title='Fecha',
        yaxis_title='Minutos',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        height=400
    )
    st.plotly_chart(fig_charge, use_container_width=True)

with tab4:
    # Financial Analysis Charts
    col_fin1, col_fin2 = st.columns(2)
    
    with col_fin1:
        # Cumulative Savings vs Investment
        # Create cumulative series
        df_fin = df_display.copy().sort_values('timestamp')
        df_fin['daily_saving'] = (df_fin['yield_wh'] / 1000) * cost_per_kwh
        df_fin['cumulative_saving'] = df_fin['daily_saving'].cumsum()
        
        fig_roi = go.Figure()
        
        # Savings Line
        fig_roi.add_trace(go.Scatter(
            x=df_fin['timestamp'],
            y=df_fin['cumulative_saving'],
            mode='lines',
            name='Ahorro Acumulado',
            line=dict(color='#4CAF50', width=3),
            fill='tozeroy'
        ))
        
        # Investment Line
        fig_roi.add_hline(
            y=roi_data['investment_clp'],
            line_dash="dash",
            line_color="#2196F3",
            annotation_text="Inversión Inicial",
            annotation_position="top right"
        )
        
        fig_roi.update_layout(
            title='Progreso del Retorno de Inversión',
            xaxis_title='Fecha',
            yaxis_title='Monto (CLP)',
            height=400,
            showlegend=True
        )
        st.plotly_chart(fig_roi, use_container_width=True)
        
    with col_fin2:
        # Monthly Savings Bar Chart
        # Resample to monthly
        df_monthly = df_fin.set_index('timestamp').resample('M')['daily_saving'].sum().reset_index()
        
        fig_monthly = px.bar(
            df_monthly,
            x='timestamp',
            y='daily_saving',
            title='Ahorro Mensual Estimado',
            labels={'daily_saving': 'Ahorro (CLP)', 'timestamp': 'Mes'},
            color='daily_saving',
            color_continuous_scale='Greens'
        )
        
        fig_monthly.update_layout(height=400)
        st.plotly_chart(fig_monthly, use_container_width=True)





with tab5:
    # SOC histogram
    fig_soc = px.histogram(
        df_display,
        x='soc',
        nbins=20,
        title='Distribución del SOC Diario',
        labels={'soc': 'SOC (%)'},
        color_discrete_sequence=['#2196F3']
    )
    
    # Add vertical lines for thresholds
    soc_warning = calculate_soc(v_warning, v_full, v_cutoff)
    soc_critical = calculate_soc(v_critical, v_full, v_cutoff)
    
    fig_soc.add_vline(x=soc_warning, line_dash="dash", line_color="#FFC107",
                      annotation_text=f"Warning ({soc_warning:.0f}%)")
    fig_soc.add_vline(x=soc_critical, line_dash="dash", line_color="#F44336",
                      annotation_text=f"Crítico ({soc_critical:.0f}%)")
    
    fig_soc.update_layout(
        xaxis_title='SOC (%)',
        yaxis_title='Días',
        height=400
    )
    st.plotly_chart(fig_soc, use_container_width=True)


st.markdown("---")


# Data table and alerts
col_table, col_alerts = st.columns([2, 1])

with col_table:
    st.subheader("📋 Datos Diarios")
    
    # Prepare display dataframe
    display_cols = ['timestamp', 'yield_wh', 'min_voltage', 'max_voltage', 'soc', 
                    'bulk_m', 'absorption_m', 'float_m', 'alert_count']
    
    df_table = df_display[display_cols].copy()
    df_table['timestamp'] = pd.to_datetime(df_table['timestamp']).dt.strftime('%Y-%m-%d')
    df_table = df_table.rename(columns={
        'timestamp': 'Fecha',
        'yield_wh': 'Producción (Wh)',
        'min_voltage': 'V Mín',
        'max_voltage': 'V Máx',
        'soc': 'SOC %',
        'bulk_m': 'Bulk (m)',
        'absorption_m': 'Abs (m)',
        'float_m': 'Float (m)',
        'alert_count': 'Alertas'
    })
    
    # Color function for SOC
    def color_soc(val):
        if val >= 60:
            return 'background-color: #C8E6C9'
        elif val >= 30:
            return 'background-color: #FFF9C4'
        else:
            return 'background-color: #FFCDD2'
    
    styled_df = df_table.head(30).style.applymap(
        color_soc, subset=['SOC %']
    ).format({
        'Producción (Wh)': '{:.0f}',
        'V Mín': '{:.1f}',
        'V Máx': '{:.1f}',
        'SOC %': '{:.1f}'
    })
    
    st.dataframe(styled_df, height=400)

with col_alerts:
    st.subheader("⚠️ Alertas Recientes")
    
    # Detect alerts for recent days
    all_alerts = []
    for _, row in df_display.head(30).iterrows():
        alerts = detect_alerts(
            min_voltage=row['min_voltage'],
            max_voltage=row['max_voltage'],
            absorption_m=row.get('absorption_m', 0),
            float_m=row.get('float_m', 0),
            error_text=row.get('error_text', ''),
            yield_wh=row.get('yield_wh')
        )
        for alert in alerts:
            all_alerts.append({
                'date': row['timestamp'].strftime('%Y-%m-%d') if pd.notna(row['timestamp']) else 'N/A',
                'alert': alert
            })
    
    if all_alerts:
        # Show critical first
        critical = [a for a in all_alerts if a['alert'].severity == Severity.CRITICAL]
        warning = [a for a in all_alerts if a['alert'].severity == Severity.WARNING]
        info = [a for a in all_alerts if a['alert'].severity == Severity.INFO]
        
        if critical:
            st.error(f"🔴 **{len(critical)} alertas críticas**")
            for a in critical[:5]:
                st.markdown(f"<div class='alert-critical'><small>{a['date']}</small><br>{a['alert'].message}</div>", 
                           unsafe_allow_html=True)
        
        if warning:
            st.warning(f"🟡 **{len(warning)} advertencias**")
            for a in warning[:5]:
                st.markdown(f"<div class='alert-warning'><small>{a['date']}</small><br>{a['alert'].message}</div>",
                           unsafe_allow_html=True)
        
        if info and not critical and not warning:
            st.info(f"ℹ️ **{len(info)} notas informativas**")
    else:
        st.success("✅ Sin alertas recientes")


st.markdown("---")


# Interpretation section
st.subheader("💡 Interpretación Automática")

interpretation = generate_interpretation(kpis)
st.markdown(interpretation)


# Custom CSS for alerts
st.markdown("""
<style>
.alert-critical {
    background-color: #ffebee;
    border-left: 4px solid #F44336;
    padding: 0.5rem;
    margin: 0.3rem 0;
    border-radius: 0 0.5rem 0.5rem 0;
    font-size: 0.85rem;
}
.alert-warning {
    background-color: #fff8e1;
    border-left: 4px solid #FFC107;
    padding: 0.5rem;
    margin: 0.3rem 0;
    border-radius: 0 0.5rem 0.5rem 0;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)
