"""
Configuration Page - System Settings

Allows users to configure thresholds, system parameters,
and application settings.
"""

import streamlit as st
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import (
    get_session_context, get_setting, set_setting, 
    get_settings_by_category, Setting
)


st.set_page_config(page_title="Configuración - Solar Monitor", page_icon="⚙️", layout="wide")

st.title("⚙️ Configuración")
st.markdown("---")


# Load current settings
thresholds = get_settings_by_category('thresholds')
system_settings = get_settings_by_category('system')
ui_settings = get_settings_by_category('ui')
financial_settings = get_settings_by_category('financial')


# Threshold settings
st.subheader("⚡ Umbrales de Voltaje")

st.info("""
**Nota sobre el cálculo de SOC:**
La estimación del estado de carga (SOC) utiliza interpolación lineal entre el voltaje de corte (0%) 
y el voltaje de flotación (100%). Esta es una aproximación práctica.

Ajusta estos valores según las especificaciones de tu fabricante o tus propias mediciones.
""")

col1, col2 = st.columns(2)

with col1:
    v_full = st.number_input(
        "V Full Pack (100% SOC)",
        min_value=40.0,
        max_value=70.0,
        value=float(thresholds.get('v_full_pack', '56.4')),
        step=0.1,
        help="Voltaje del pack cuando está completamente cargado (float). Default: 56.4V para 4×12V NARADA"
    )
    
    v_warning = st.number_input(
        "V Warning (Descarga profunda)",
        min_value=35.0,
        max_value=55.0,
        value=float(thresholds.get('v_warning', '44.0')),
        step=0.5,
        help="Voltaje de advertencia para descarga profunda. Default: 44V"
    )

with col2:
    v_cutoff = st.number_input(
        "V Cutoff (0% SOC)",
        min_value=30.0,
        max_value=50.0,
        value=float(thresholds.get('v_cutoff', '37.5')),
        step=0.5,
        help="Voltaje de corte del sistema (0% SOC). Default: 37.5V"
    )
    
    v_critical = st.number_input(
        "V Critical (Descarga crítica)",
        min_value=35.0,
        max_value=50.0,
        value=float(thresholds.get('v_critical', '42.0')),
        step=0.5,
        help="Voltaje crítico de descarga. Default: 42V"
    )


# Voltage visualization
st.markdown("### 📊 Visualización de Rangos")

# Create a simple gauge-like visualization
import plotly.graph_objects as go

fig = go.Figure()

# Add colored ranges
fig.add_trace(go.Bar(
    x=[v_cutoff - 35],
    y=['Voltaje'],
    orientation='h',
    name='Cutoff',
    marker_color='#F44336',
    base=35
))

fig.add_trace(go.Bar(
    x=[v_critical - v_cutoff],
    y=['Voltaje'],
    orientation='h',
    name='Crítico',
    marker_color='#FF9800',
    base=v_cutoff
))

fig.add_trace(go.Bar(
    x=[v_warning - v_critical],
    y=['Voltaje'],
    orientation='h',
    name='Warning',
    marker_color='#FFC107',
    base=v_critical
))

fig.add_trace(go.Bar(
    x=[v_full - v_warning],
    y=['Voltaje'],
    orientation='h',
    name='Normal',
    marker_color='#4CAF50',
    base=v_warning
))

fig.update_layout(
    barmode='stack',
    height=100,
    showlegend=True,
    legend=dict(orientation='h', yanchor='bottom', y=1.02),
    xaxis=dict(title='Voltaje (V)', range=[35, 60]),
    yaxis=dict(visible=False),
    margin=dict(l=20, r=20, t=50, b=20)
)

st.plotly_chart(fig, use_container_width=True)


st.markdown("---")


# System settings
st.subheader("🔋 Configuración del Sistema")

col1, col2 = st.columns(2)

with col1:
    system_power = st.number_input(
        "Potencia instalada (kW)",
        min_value=0.5,
        max_value=50.0,
        value=float(system_settings.get('system_power_kw', '5.0')),
        step=0.5,
        help="Potencia total del sistema fotovoltaico"
    )
    
    battery_count = st.number_input(
        "Número de baterías en serie",
        min_value=1,
        max_value=16,
        value=int(system_settings.get('battery_count', '4')),
        step=1,
        help="Cantidad de baterías conectadas en serie"
    )
    
    battery_voltage = st.number_input(
        "Voltaje por batería (V)",
        min_value=6,
        max_value=48,
        value=int(system_settings.get('battery_voltage', '12')),
        step=6,
        help="Voltaje nominal de cada batería"
    )

with col2:
    battery_capacity = st.number_input(
        "Capacidad por batería (Ah)",
        min_value=50,
        max_value=1000,
        value=int(system_settings.get('battery_capacity_ah', '200')),
        step=50,
        help="Capacidad nominal de cada batería"
    )
    
    battery_model = st.text_input(
        "Modelo de batería",
        value=system_settings.get('battery_model', 'NARADA MPG12V200'),
        help="Modelo/marca de las baterías"
    )

# Show calculated values
pack_voltage = battery_count * battery_voltage
pack_capacity_wh = pack_voltage * battery_capacity

st.markdown(f"""
**Valores calculados del banco:**
- Voltaje nominal del pack: **{pack_voltage}V** ({battery_count} × {battery_voltage}V)
- Capacidad total: **{pack_capacity_wh/1000:.1f} kWh** ({pack_voltage}V × {battery_capacity}Ah)
""")


st.markdown("---")


# Financial Settings
st.subheader("💰 Configuración Financiera")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 💵 Inversión")
    initial_investment = st.number_input(
        "Inversión Inicial Sistema (CLP)",
        min_value=0,
        value=int(float(financial_settings.get('initial_investment', '5000000'))),
        step=100000,
        format="%d",
        help="Costo total de instalación del sistema"
    )
    
    usd_rate = st.number_input(
        "Tipo de Cambio (CLP -> USD)",
        min_value=100,
        value=int(float(financial_settings.get('usd_clp_rate', '950'))),
        step=10,
        help="Valor del dólar para calcular ahorros en USD"
    )

with col2:
    st.markdown("#### 🧾 Costos de Red (Tarifas)")
    cost_kwh = st.number_input(
        "Costo por kWh Consumido (CLP)",
        min_value=0.0,
        value=float(financial_settings.get('cost_kwh', '235.45')),
        step=1.0,
        format="%.2f"
    )
    
    st.caption("Cargos Fijos Mensuales (Estimados)")
    c_sub1, c_sub2, c_sub3 = st.columns(3)
    with c_sub1:
        cost_admin = st.number_input("Admin.", value=int(float(financial_settings.get('cost_admin', '1195'))))
    with c_sub2:
        cost_transport = st.number_input("Transporte", value=int(float(financial_settings.get('cost_transport', '3500'))))
    with c_sub3:
        cost_meter = st.number_input("Medidor", value=int(float(financial_settings.get('cost_meter_rent', '438'))))


st.markdown("---")


# UI Settings
st.subheader("🎨 Preferencias de Interfaz")

col1, col2 = st.columns(2)

with col1:
    timezone = st.selectbox(
        "Zona horaria",
        options=['America/Santiago', 'UTC', 'America/Buenos_Aires', 'America/Lima', 'America/Bogota'],
        index=['America/Santiago', 'UTC', 'America/Buenos_Aires', 'America/Lima', 'America/Bogota'].index(
            ui_settings.get('timezone', 'America/Santiago')
        ),
        help="Zona horaria para interpretar fechas de los CSV"
    )

with col2:
    st.markdown("**Colores del tema:**")
    col_a, col_b = st.columns(2)
    with col_a:
        color_success = st.color_picker("Éxito", ui_settings.get('color_success', '#4CAF50'))
        color_warning = st.color_picker("Warning", ui_settings.get('color_warning', '#FFC107'))
    with col_b:
        color_info = st.color_picker("Info", ui_settings.get('color_info', '#2196F3'))
        color_danger = st.color_picker("Danger", ui_settings.get('color_danger', '#F44336'))


st.markdown("---")


# Save button
if st.button("💾 Guardar Configuración", type="primary", use_container_width=True):
    try:
        # Save thresholds
        set_setting('v_full_pack', str(v_full), 'thresholds', 'Full pack voltage at 100% SOC')
        set_setting('v_cutoff', str(v_cutoff), 'thresholds', 'Cutoff voltage at 0% SOC')
        set_setting('v_warning', str(v_warning), 'thresholds', 'Warning threshold for deep discharge')
        set_setting('v_critical', str(v_critical), 'thresholds', 'Critical threshold for discharge')
        
        # Save system settings
        set_setting('system_power_kw', str(system_power), 'system', 'Installed system power in kW')
        set_setting('battery_count', str(battery_count), 'system', 'Number of batteries in series')
        set_setting('battery_voltage', str(battery_voltage), 'system', 'Individual battery voltage (V)')
        set_setting('battery_capacity_ah', str(battery_capacity), 'system', 'Battery capacity in Ah')
        set_setting('battery_model', battery_model, 'system', 'Battery model name')
        
        # Save Financial settings
        set_setting('initial_investment', str(initial_investment), 'financial', 'Initial investment in CLP')
        set_setting('usd_clp_rate', str(usd_rate), 'financial', 'Exchange rate CLP to USD')
        set_setting('cost_kwh', str(cost_kwh), 'financial', 'Cost per kWh (CLP)')
        set_setting('cost_admin', str(cost_admin), 'financial', 'Monthly administration fixed cost')
        set_setting('cost_transport', str(cost_transport), 'financial', 'Monthly transport fixed cost')
        set_setting('cost_meter_rent', str(cost_meter), 'financial', 'Monthly meter rental cost')
        
        # Save UI settings
        set_setting('timezone', timezone, 'ui', 'Timezone for date parsing')
        set_setting('color_success', color_success, 'ui', 'Success/good color (green)')
        set_setting('color_info', color_info, 'ui', 'Info color (blue)')
        set_setting('color_warning', color_warning, 'ui', 'Warning color (amber)')
        set_setting('color_danger', color_danger, 'ui', 'Danger/critical color (red)')
        
        st.success("✅ Configuración guardada exitosamente.")
        st.balloons()
        
    except Exception as e:
        st.error(f"❌ Error al guardar: {str(e)}")


st.markdown("---")


# Reset to defaults
st.subheader("🔄 Restaurar Valores por Defecto")

with st.expander("Restaurar configuración original"):
    st.warning("Esto restaurará todos los ajustes a sus valores por defecto.")
    
    if st.button("🔄 Restaurar Defaults"):
        # Default values
        defaults = {
            # Thresholds
            'v_full_pack': ('56.4', 'thresholds'),
            'v_cutoff': ('37.5', 'thresholds'),
            'v_warning': ('44.0', 'thresholds'),
            'v_critical': ('42.0', 'thresholds'),
            # System
            'system_power_kw': ('5.0', 'system'),
            'battery_count': ('4', 'system'),
            'battery_voltage': ('12', 'system'),
            'battery_capacity_ah': ('200', 'system'),
            'battery_model': ('NARADA MPG12V200', 'system'),
            # Financial
            'initial_investment': ('5000000', 'financial'),
            'cost_admin': ('1195', 'financial'),
            'cost_transport': ('3500', 'financial'),
            'cost_kwh': ('235.45', 'financial'),
            'cost_meter_rent': ('438', 'financial'),
            'usd_clp_rate': ('950', 'financial'),
            # UI
            'timezone': ('America/Santiago', 'ui'),
            'color_success': ('#4CAF50', 'ui'),
            'color_info': ('#2196F3', 'ui'),
            'color_warning': ('#FFC107', 'ui'),
            'color_danger': ('#F44336', 'ui'),
        }
        
        for key, (value, category) in defaults.items():
            set_setting(key, value, category)
        
        st.success("✅ Configuración restaurada a valores por defecto.")
        st.rerun()


# Database info
st.markdown("---")
st.subheader("📊 Información de la Base de Datos")

with get_session_context() as session:
    from src.database import Record, Alert
    
    record_count = session.query(Record).count()
    alert_count = session.query(Alert).count()
    setting_count = session.query(Setting).count()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Registros de datos", record_count)
    with col2:
        st.metric("Alertas almacenadas", alert_count)
    with col3:
        st.metric("Configuraciones", setting_count)

# Database path
from src.database.connection import get_db_path
db_path = get_db_path()
st.caption(f"📁 Base de datos: `{db_path}`")
