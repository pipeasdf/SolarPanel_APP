"""
Solar Panel Monitoring App - Main Entry Point

A Streamlit-based application for monitoring Victron solar systems.
Analyzes CSV data, calculates SOC, and provides interactive dashboards.

Run with: streamlit run app.py
"""

import streamlit as st
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.database import init_db, get_setting


# Page configuration
st.set_page_config(
    page_title="Solar Monitor - Victron",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Sistema de monitoreo para paneles solares Victron. "
                 "Desarrollado para sistemas fotovoltaicos de 48V."
    }
)

# Initialize database on first run
@st.cache_resource
def initialize():
    """Initialize database and return status."""
    init_db()
    return True

# Run initialization
initialize()


# Custom CSS for styling
st.markdown("""
<style>
    /* Main color scheme */
    :root {
        --success-color: #4CAF50;
        --info-color: #2196F3;
        --warning-color: #FFC107;
        --danger-color: #F44336;
        --background-color: #F5F5F5;
    }
    
    /* Header styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1a1a2e;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #4CAF50;
        margin-bottom: 2rem;
    }
    
    /* KPI cards */
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
        transition: transform 0.3s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-5px);
    }
    
    .kpi-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    
    .kpi-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    /* SOC color classes */
    .soc-excellent { background-color: #4CAF50; color: white; }
    .soc-good { background-color: #8BC34A; color: white; }
    .soc-moderate { background-color: #FFC107; color: black; }
    .soc-low { background-color: #FF9800; color: white; }
    .soc-critical { background-color: #F44336; color: white; }
    
    /* Alert styling */
    .alert-critical {
        background-color: #ffebee;
        border-left: 4px solid #F44336;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
    }
    
    .alert-warning {
        background-color: #fff8e1;
        border-left: 4px solid #FFC107;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
    }
    
    .alert-info {
        background-color: #e3f2fd;
        border-left: 4px solid #2196F3;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
    }
    
    /* Sidebar styling */
    .sidebar-info {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #666;
        font-size: 0.85rem;
    }
    
    /* Table styling */
    .dataframe {
        font-size: 0.9rem;
    }
    
    /* Metric cards improvement */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    
    /* Better spacing for columns */
    .row-widget.stHorizontalBlock {
        gap: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# Main content
st.markdown('<h1 class="main-header">☀️ Solar Monitor</h1>', unsafe_allow_html=True)

# Welcome message
st.markdown("""
### Bienvenido al Sistema de Monitoreo Solar

Esta aplicación te permite analizar los datos de tu sistema fotovoltaico Victron:

- **📊 Dashboard**: Visualiza KPIs, gráficos de producción, voltajes y alertas
- **📤 Upload**: Sube archivos CSV exportados de tu controlador Victron
- **📁 Histórico**: Explora y exporta tus datos almacenados
- **⚙️ Configuración**: Ajusta umbrales y parámetros del sistema

---
""")

# Sidebar with system info
with st.sidebar:
    st.markdown("### ⚡ Sistema")
    
    # Load system settings
    system_power = get_setting('system_power_kw', '5.0')
    battery_model = get_setting('battery_model', 'NARADA MPG12V200')
    battery_count = get_setting('battery_count', '4')
    battery_voltage = get_setting('battery_voltage', '12')
    battery_capacity = get_setting('battery_capacity_ah', '200')
    
    st.markdown(f"""
    <div class="sidebar-info">
        <strong>Potencia instalada:</strong> {system_power} kW<br>
        <strong>Baterías:</strong> {battery_count}× {battery_model}<br>
        <strong>Banco:</strong> {int(float(battery_voltage)) * int(battery_count)}V, {battery_capacity}Ah
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📍 Ubicación")
    st.markdown("La Unión, Los Ríos, Chile")
    
    st.markdown("---")
    st.markdown("### ℹ️ Notas")
    st.info("""
    **SOC Estimation**: La estimación del estado de carga 
    usa interpolación lineal entre el voltaje de corte 
    y el voltaje de flotación. Es una aproximación 
    práctica que puede ajustarse en Configuración.
    """)


# Quick start guide
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 🚀 Inicio Rápido
    
    1. Ve a **📤 Upload** en el menú lateral
    2. Sube tu archivo CSV de Victron
    3. Revisa la validación de columnas
    4. Confirma la importación
    5. Explora el **📊 Dashboard**
    """)

with col2:
    st.markdown("""
    ### 📋 Formato CSV Esperado
    
    El sistema acepta CSV con estas columnas:
    - `Date` o `Timestamp` - Fecha/hora
    - `Yield(Wh)` - Producción diaria
    - `Min. battery voltage(V)` - Voltaje mínimo
    - `Max. battery voltage(V)` - Voltaje máximo
    - `Time in bulk/absorption/float(m)` - Tiempos de carga
    """)


# Info about thresholds
st.markdown("---")
st.markdown("### ⚡ Umbrales del Sistema")

col1, col2, col3, col4 = st.columns(4)

v_full = get_setting('v_full_pack', '56.4')
v_cutoff = get_setting('v_cutoff', '37.5')
v_warning = get_setting('v_warning', '44.0')
v_critical = get_setting('v_critical', '42.0')

with col1:
    st.metric("100% SOC (Float)", f"{v_full}V", help="Voltaje del pack al 100% SOC")
    
with col2:
    st.metric("0% SOC (Cutoff)", f"{v_cutoff}V", help="Voltaje de corte del sistema")
    
with col3:
    st.metric("Warning", f"{v_warning}V", help="Umbral de descarga profunda")
    
with col4:
    st.metric("Crítico", f"{v_critical}V", help="Umbral de descarga crítica")


# Footer
st.markdown("---")
st.markdown("""
<div class="footer">
    Solar Monitor v1.0 | Desarrollado para sistemas Victron | 
    Zona horaria: America/Santiago
</div>
""", unsafe_allow_html=True)
