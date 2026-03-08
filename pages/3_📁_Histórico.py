"""
Historical Data Page - Browse and Export

Allows users to browse stored data, filter by date range,
and export to CSV/Excel formats.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_session_context, get_setting, Record
from src.calculations import (
    calculate_soc, calculate_kpis, get_daily_dataframe,
    calculate_monthly_stats, compare_periods
)
from src.utils.export import (
    export_to_csv, export_to_excel, format_dataframe_for_export,
    generate_report_summary
)


st.set_page_config(page_title="Histórico - Solar Monitor", page_icon="📁", layout="wide")

st.title("📁 Histórico de Datos")
st.markdown("---")


@st.cache_data(ttl=60)
def load_all_data():
    """Load all records from database."""
    with get_session_context() as session:
        records = session.query(Record).order_by(Record.timestamp.desc()).all()
        
        if not records:
            return pd.DataFrame()
        
        data = [{
            'id': r.id,
            'timestamp': r.timestamp,
            'yield_wh': r.yield_wh,
            'min_voltage': r.min_voltage,
            'max_voltage': r.max_voltage,
            'bulk_m': r.bulk_m,
            'absorption_m': r.absorption_m,
            'float_m': r.float_m,
            'pv_power_max': r.pv_power_max,
            'pv_voltage_max': r.pv_voltage_max,
            'error_text': r.error_text,
            'created_at': r.created_at
        } for r in records]
        
        return pd.DataFrame(data)


# Load data
df_all = load_all_data()

if df_all.empty:
    st.warning("⚠️ No hay datos almacenados. Por favor, sube un archivo CSV en la página de Upload.")
    st.stop()

# Get settings
v_full = float(get_setting('v_full_pack', '56.4'))
v_cutoff = float(get_setting('v_cutoff', '37.5'))
v_warning = float(get_setting('v_warning', '44.0'))


# Sidebar filters
with st.sidebar:
    st.header("🔍 Filtros")
    
    # Date range filter
    min_date = df_all['timestamp'].min().date() if pd.notna(df_all['timestamp'].min()) else date.today() - timedelta(days=365)
    max_date = df_all['timestamp'].max().date() if pd.notna(df_all['timestamp'].max()) else date.today()
    
    date_from = st.date_input(
        "Desde",
        value=max(min_date, max_date - timedelta(days=30)),
        min_value=min_date,
        max_value=max_date
    )
    
    date_to = st.date_input(
        "Hasta",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )
    
    st.markdown("---")
    
    # Quick filters
    st.subheader("Filtros Rápidos")
    
    show_deep_discharge = st.checkbox("Solo días con descarga profunda", value=False)
    show_no_absorption = st.checkbox("Solo días sin absorción", value=False)
    show_errors = st.checkbox("Solo días con errores", value=False)


# Filter data
df_filtered = df_all.copy()
df_filtered['date'] = pd.to_datetime(df_filtered['timestamp']).dt.date

# Apply date filter
df_filtered = df_filtered[
    (df_filtered['date'] >= date_from) & 
    (df_filtered['date'] <= date_to)
]

# Apply quick filters
if show_deep_discharge:
    df_filtered = df_filtered[df_filtered['min_voltage'] < v_warning]

if show_no_absorption:
    df_filtered = df_filtered[df_filtered['absorption_m'] == 0]

if show_errors:
    df_filtered = df_filtered[
        df_filtered['error_text'].notna() & 
        (df_filtered['error_text'] != '') &
        (df_filtered['error_text'] != 'nan')
    ]


# Add SOC calculation
df_display = get_daily_dataframe(df_filtered, v_full, v_cutoff, v_warning)


# Stats summary
st.subheader("📊 Resumen del Período")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Registros", len(df_display))

with col2:
    if not df_display.empty:
        total_kwh = df_display['yield_wh'].sum() / 1000
        st.metric("Producción Total", f"{total_kwh:.1f} kWh")
    else:
        st.metric("Producción Total", "0 kWh")

with col3:
    if not df_display.empty:
        avg_soc = df_display['soc'].mean()
        st.metric("SOC Promedio", f"{avg_soc:.1f}%")
    else:
        st.metric("SOC Promedio", "N/A")

with col4:
    if not df_display.empty:
        deep_days = (df_display['min_voltage'] < v_warning).sum()
        st.metric("Días Descarga Profunda", deep_days)
    else:
        st.metric("Días Descarga Profunda", 0)


st.markdown("---")


# Data table
st.subheader("📋 Datos")

# Select columns to show
with st.expander("⚙️ Columnas a mostrar"):
    col_options = {
        'timestamp': 'Fecha/Hora',
        'yield_wh': 'Producción (Wh)',
        'min_voltage': 'V Mín',
        'max_voltage': 'V Máx',
        'soc': 'SOC %',
        'bulk_m': 'Bulk (min)',
        'absorption_m': 'Absorción (min)',
        'float_m': 'Flotación (min)',
        'pv_power_max': 'Potencia PV Máx',
        'pv_voltage_max': 'Voltaje PV Máx',
        'error_text': 'Errores',
        'is_deep_discharge': 'Desc. Profunda',
        'alert_count': 'Alertas'
    }
    
    default_cols = ['timestamp', 'yield_wh', 'min_voltage', 'max_voltage', 'soc', 
                    'bulk_m', 'absorption_m', 'float_m', 'alert_count']
    
    selected_cols = st.multiselect(
        "Seleccionar columnas",
        options=list(col_options.keys()),
        default=default_cols,
        format_func=lambda x: col_options.get(x, x)
    )

# Display table
if not df_display.empty and selected_cols:
    # Prepare display data
    df_show = df_display[[c for c in selected_cols if c in df_display.columns]].copy()
    
    # Format timestamp
    if 'timestamp' in df_show.columns:
        df_show['timestamp'] = pd.to_datetime(df_show['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Rename columns
    df_show = df_show.rename(columns=col_options)
    
    # Color SOC column
    def color_soc(val):
        if pd.isna(val):
            return ''
        if val >= 60:
            return 'background-color: #C8E6C9'
        elif val >= 30:
            return 'background-color: #FFF9C4'
        else:
            return 'background-color: #FFCDD2'
    
    if 'SOC %' in df_show.columns:
        styled = df_show.style.applymap(color_soc, subset=['SOC %']).format({
            'Producción (Wh)': '{:.0f}',
            'V Mín': '{:.2f}',
            'V Máx': '{:.2f}',
            'SOC %': '{:.1f}'
        }, na_rep='')
    else:
        styled = df_show
    
    st.dataframe(styled, height=400)
else:
    st.info("No hay datos para mostrar con los filtros actuales.")


st.markdown("---")


# Export section
st.subheader("📥 Exportar Datos")

col_export1, col_export2 = st.columns(2)

with col_export1:
    st.markdown("**Exportar datos filtrados**")
    
    export_format = st.radio(
        "Formato de exportación",
        options=['CSV', 'Excel'],
        horizontal=True
    )
    
    if not df_display.empty:
        # Prepare export data
        export_cols = ['timestamp', 'yield_wh', 'min_voltage', 'max_voltage', 'soc',
                       'bulk_m', 'absorption_m', 'float_m']
        export_cols = [c for c in export_cols if c in df_display.columns]
        
        df_export = format_dataframe_for_export(df_display[export_cols])
        
        if export_format == 'CSV':
            csv_buffer = export_to_csv(df_export)
            st.download_button(
                label="📥 Descargar CSV",
                data=csv_buffer,
                file_name=f"solar_data_{date_from}_{date_to}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            # Calculate KPIs for summary sheet
            kpis = calculate_kpis(df_display, v_full, v_cutoff, v_warning)
            summary_df = generate_report_summary(kpis, date_from, date_to)
            
            excel_buffer = export_to_excel(
                df_export,
                sheet_name='Datos',
                additional_sheets={'Resumen': summary_df}
            )
            st.download_button(
                label="📥 Descargar Excel",
                data=excel_buffer,
                file_name=f"solar_data_{date_from}_{date_to}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        st.info("No hay datos para exportar.")

with col_export2:
    st.markdown("**Estadísticas mensuales**")
    
    if not df_all.empty:
        monthly_stats = calculate_monthly_stats(df_all, v_full, v_cutoff)
        
        if not monthly_stats.empty:
            # Show monthly summary
            st.dataframe(
                monthly_stats[['month_str', 'total_yield_kwh', 'avg_soc', 'days_count']].rename(columns={
                    'month_str': 'Mes',
                    'total_yield_kwh': 'Producción (kWh)',
                    'avg_soc': 'SOC Promedio (%)',
                    'days_count': 'Días'
                }).head(12),
                use_container_width=True,
                hide_index=True
            )
            
            # Export monthly data
            monthly_csv = export_to_csv(monthly_stats)
            st.download_button(
                label="📥 Descargar Estadísticas Mensuales",
                data=monthly_csv,
                file_name="solar_monthly_stats.csv",
                mime="text/csv",
                use_container_width=True
            )


st.markdown("---")


# Comparison section
st.subheader("📊 Comparar Períodos")

with st.expander("Comparar dos períodos"):
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        st.markdown("**Período 1**")
        p1_start = st.date_input("Inicio P1", value=max_date - timedelta(days=60), key="p1_start")
        p1_end = st.date_input("Fin P1", value=max_date - timedelta(days=31), key="p1_end")
    
    with col_p2:
        st.markdown("**Período 2**")
        p2_start = st.date_input("Inicio P2", value=max_date - timedelta(days=30), key="p2_start")
        p2_end = st.date_input("Fin P2", value=max_date, key="p2_end")
    
    if st.button("Comparar", use_container_width=True):
        comparison = compare_periods(df_all, p1_start, p1_end, p2_start, p2_end, v_full, v_cutoff)
        
        col_r1, col_r2, col_r3 = st.columns(3)
        
        with col_r1:
            st.markdown("**Período 1**")
            st.metric("Producción", f"{comparison['period1']['kpis'].total_yield_kwh:.1f} kWh")
            st.metric("SOC Promedio", f"{comparison['period1']['kpis'].average_soc:.1f}%")
            st.metric("Días", comparison['period1']['kpis'].total_days)
        
        with col_r2:
            st.markdown("**Período 2**")
            st.metric("Producción", f"{comparison['period2']['kpis'].total_yield_kwh:.1f} kWh")
            st.metric("SOC Promedio", f"{comparison['period2']['kpis'].average_soc:.1f}%")
            st.metric("Días", comparison['period2']['kpis'].total_days)
        
        with col_r3:
            st.markdown("**Diferencia**")
            diff = comparison['differences']
            if diff['yield_pct'] is not None:
                delta_color = "normal" if diff['yield_pct'] >= 0 else "inverse"
                st.metric(
                    "Cambio Producción",
                    f"{diff['yield_kwh']:.1f} kWh",
                    delta=f"{diff['yield_pct']:.1f}%",
                    delta_color=delta_color
                )
            if diff['avg_soc'] is not None:
                st.metric(
                    "Cambio SOC",
                    f"{diff['avg_soc']:.1f}%"
                )


# Data management
st.markdown("---")
st.subheader("🗑️ Gestión de Datos")

with st.expander("⚠️ Eliminar datos (usar con cuidado)"):
    st.warning("Esta acción no se puede deshacer.")
    
    delete_option = st.radio(
        "¿Qué deseas eliminar?",
        options=['Nada', 'Datos del período seleccionado', 'Todos los datos'],
        index=0
    )
    
    if delete_option != 'Nada':
        confirm_text = st.text_input("Escribe 'CONFIRMAR' para proceder")
        
        if confirm_text == 'CONFIRMAR':
            if st.button("🗑️ Eliminar", type="secondary"):
                with get_session_context() as session:
                    if delete_option == 'Datos del período seleccionado':
                        deleted = session.query(Record).filter(
                            Record.timestamp >= datetime.combine(date_from, datetime.min.time()),
                            Record.timestamp <= datetime.combine(date_to, datetime.max.time())
                        ).delete()
                        st.success(f"Se eliminaron {deleted} registros del período seleccionado.")
                    else:
                        deleted = session.query(Record).delete()
                        st.success(f"Se eliminaron todos los {deleted} registros.")
                
                # Clear cache and rerun outside transaction to avoid rollback
                st.cache_data.clear()
                st.rerun()
