"""
Financial History Page - Solar Panel Monitoring

Detailed monthly breakdown of savings and theoretical grid bill costs.
Includes optional in-memory simulation for missing calendar months.
"""

import streamlit as st
import pandas as pd
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


# ---------------------------------------------------------------------------
# Data Loading (unchanged logic)
# ---------------------------------------------------------------------------
def load_monthly_data():
    with get_session_context() as session:
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

        monthly = df.groupby(['year', 'month']).agg({
            'yield_wh': 'sum'
        }).reset_index()

        monthly['date_str'] = monthly.apply(
            lambda x: f"{int(x['year'])}-{int(x['month']):02d}", axis=1
        )
        monthly['date_dt'] = pd.to_datetime(monthly['date_str'])
        monthly['yield_kwh'] = monthly['yield_wh'] / 1000.0
        monthly['savings_clp'] = monthly['yield_kwh'] * cost_kwh
        monthly['savings_usd'] = monthly['savings_clp'] / usd_rate
        monthly['theoretical_bill_clp'] = monthly['yield_kwh'].apply(
            lambda kwh: calculate_theoretical_bill(kwh, financial_settings)
        )
        monthly['avoided_cost_clp'] = monthly['theoretical_bill_clp']

        return monthly.sort_values('date_dt', ascending=False)


# ---------------------------------------------------------------------------
# Gap detection helper
# ---------------------------------------------------------------------------
def detect_missing_months(df_monthly: pd.DataFrame, custom_start=None) -> pd.DataFrame:
    """Return a DataFrame of calendar months missing.

    Tramo 1 – months from *custom_start* up to (but not including) the first
    real record month.
    Tramo 2 – gaps between existing records up to the current month.

    Each row includes a 'tramo' column for identification.
    """
    if df_monthly.empty:
        return pd.DataFrame()

    first_date = df_monthly['date_dt'].min()
    now = datetime.now()
    current_month_start = datetime(now.year, now.month, 1)

    rows: list[dict] = []

    # Tramo 1: pre-record period
    if custom_start is not None and custom_start < first_date:
        pre_end = first_date - pd.DateOffset(months=1)
        pre_range = pd.date_range(start=custom_start, end=pre_end, freq='MS')
        for dt in pre_range:
            rows.append({
                'year': dt.year,
                'month': dt.month,
                'date_str': f"{dt.year}-{dt.month:02d}",
                'tramo': 'Previo al sistema',
            })

    # Tramo 2: gaps between existing records
    full_range = pd.date_range(start=first_date, end=current_month_start, freq='MS')
    existing = set(df_monthly['date_dt'].dt.to_period('M'))

    for dt in full_range:
        if dt.to_period('M') not in existing:
            rows.append({
                'year': dt.year,
                'month': dt.month,
                'date_str': f"{dt.year}-{dt.month:02d}",
                'tramo': 'Gap entre registros',
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main page flow
# ---------------------------------------------------------------------------
df_monthly = load_monthly_data()

if df_monthly.empty:
    st.warning("No hay datos históricos suficientes para mostrar el análisis.")
    st.stop()

# --- Filters & simulation toggle ---
col_filter, col_sim, _ = st.columns([1, 1.5, 1.5])
with col_filter:
    years = sorted(df_monthly['year'].unique(), reverse=True)
    selected_year = st.selectbox("Seleccionar Año", options=["Todos"] + list(years))

with col_sim:
    st.write("")  # vertical spacer
    sim_enabled = st.checkbox("🔮 Simular meses sin registro", key="sim_enabled")

# ---------------------------------------------------------------------------
# Build simulation DataFrame (in-memory only)
# ---------------------------------------------------------------------------
df_simulated = pd.DataFrame()

if sim_enabled:
    first_record_date = df_monthly['date_dt'].min()
    first_record_year = int(first_record_date.year)
    first_record_month = int(first_record_date.month)

    # Default start: one month before the first real record
    if first_record_month == 1:
        _def_month, _def_year = 12, first_record_year - 1
    else:
        _def_month, _def_year = first_record_month - 1, first_record_year

    if 'sim_start_month' not in st.session_state:
        st.session_state['sim_start_month'] = _def_month
    if 'sim_start_year' not in st.session_state:
        st.session_state['sim_start_year'] = _def_year

    df_missing = pd.DataFrame()

    with st.expander("⚙️ Configuración de Simulación", expanded=True):
        # ── Date-range configuration ──────────────────────────────────
        st.markdown("##### 📅 Fecha de inicio del sistema solar")
        col_m, col_y = st.columns(2)
        _month_names = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
        ]

        with col_m:
            sel_month = st.selectbox(
                "Mes de inicio",
                options=list(range(1, 13)),
                format_func=lambda m: _month_names[m - 1],
                index=st.session_state['sim_start_month'] - 1,
                key="sim_start_month_select",
            )
        with col_y:
            _now_dt = datetime.now()
            _year_opts = list(range(2005, _now_dt.year + 1))
            _yr_idx = (
                _year_opts.index(st.session_state['sim_start_year'])
                if st.session_state['sim_start_year'] in _year_opts
                else len(_year_opts) - 1
            )
            sel_year = st.selectbox(
                "Año de inicio",
                options=_year_opts,
                index=_yr_idx,
                key="sim_start_year_select",
            )

        # Persist selection
        st.session_state['sim_start_month'] = sel_month
        st.session_state['sim_start_year'] = sel_year

        # Validate: custom start must be strictly before first real record
        custom_start = datetime(sel_year, sel_month, 1)
        if custom_start >= first_record_date:
            custom_start = None
            st.warning(
                "La fecha seleccionada no es anterior al primer registro real. "
                "Solo se simularán gaps entre registros existentes."
            )

        # Detect all missing months (both tranches)
        df_missing = detect_missing_months(df_monthly, custom_start)

        if df_missing.empty:
            st.success("No se detectaron meses faltantes. 🎉")
            if 'sim_table_data' in st.session_state:
                del st.session_state['sim_table_data']
        else:
            # ── Informative breakdown ─────────────────────────────────
            n_previo = int((df_missing['tramo'] == 'Previo al sistema').sum())
            n_gaps = int((df_missing['tramo'] == 'Gap entre registros').sum())

            _info_parts = []
            if n_previo > 0:
                _pre = df_missing[df_missing['tramo'] == 'Previo al sistema']
                _info_parts.append(
                    f"**{n_previo}** meses anteriores a tus registros "
                    f"({_pre.iloc[0]['date_str']} → {_pre.iloc[-1]['date_str']})"
                )
            if n_gaps > 0:
                _info_parts.append(f"**{n_gaps}** meses entre registros existentes")

            st.info("Se simularán: " + " más ".join(_info_parts))
            st.markdown("---")

            # ── Separate kWh averages ─────────────────────────────────
            avg_kwh_real = round(float(df_monthly['yield_kwh'].mean()), 2)

            col_avg1, col_avg2 = st.columns(2)
            with col_avg1:
                avg_kwh_early = st.number_input(
                    "Promedio estimado período inicial (kWh)",
                    min_value=0.0,
                    value=float(st.session_state.get('sim_kwh_early_period', avg_kwh_real)),
                    step=1.0,
                    format="%.2f",
                    key="sim_kwh_early_input",
                    help="Valor por defecto para meses anteriores al primer registro",
                )
                st.session_state['sim_kwh_early_period'] = avg_kwh_early

            with col_avg2:
                avg_kwh = st.number_input(
                    "Promedio estimado gaps intermedios (kWh)",
                    min_value=0.0,
                    value=avg_kwh_real,
                    step=1.0,
                    format="%.2f",
                    key="sim_avg_kwh",
                )

            # ── Editable table with Período column ────────────────────
            init_key = "sim_table_data"
            _current_months = set(df_missing['date_str'].tolist())
            needs_init = (
                init_key not in st.session_state
                or len(st.session_state[init_key]) != len(df_missing)
                or set(st.session_state[init_key]['Mes'].tolist()) != _current_months
            )

            if needs_init:
                _tbl = df_missing[['date_str', 'tramo']].copy()
                _tbl['kWh Estimado'] = _tbl['tramo'].apply(
                    lambda t: avg_kwh_early if t == 'Previo al sistema' else avg_kwh
                )
                _tbl = _tbl.rename(columns={'date_str': 'Mes', 'tramo': 'Período'})
                st.session_state[init_key] = _tbl

            # Reset button (respects per-tranche defaults)
            if st.button("↻ Resetear todos al promedio"):
                _df_reset = st.session_state[init_key].copy()
                _mask_pre = _df_reset['Período'] == 'Previo al sistema'
                _df_reset.loc[_mask_pre, 'kWh Estimado'] = avg_kwh_early
                _df_reset.loc[~_mask_pre, 'kWh Estimado'] = avg_kwh
                st.session_state[init_key] = _df_reset

            edited_df = st.data_editor(
                st.session_state[init_key],
                disabled=["Mes", "Período"],
                use_container_width=True,
                num_rows="fixed",
                key="sim_editor",
            )
            # Persist edits
            st.session_state[init_key] = edited_df

            st.info(f"Se simularán **{len(edited_df)}** meses faltantes en total.")

    # Build the simulated rows using same financial formulas as real data
    if 'sim_table_data' in st.session_state and not st.session_state['sim_table_data'].empty:
        _ed = st.session_state['sim_table_data']
        sim_rows = []
        for _, row in _ed.iterrows():
            kwh = float(row["kWh Estimado"])
            parts = str(row["Mes"]).split("-")
            yr, mo = int(parts[0]), int(parts[1])
            sav_clp = kwh * cost_kwh
            sim_rows.append({
                'year': yr,
                'month': mo,
                'date_str': row["Mes"],
                'date_dt': pd.Timestamp(year=yr, month=mo, day=1),
                'yield_wh': kwh * 1000.0,
                'yield_kwh': kwh,
                'savings_clp': sav_clp,
                'savings_usd': sav_clp / usd_rate,
                'theoretical_bill_clp': calculate_theoretical_bill(kwh, financial_settings),
                'avoided_cost_clp': calculate_theoretical_bill(kwh, financial_settings),
                'es_simulado': True,
            })
        df_simulated = pd.DataFrame(sim_rows)

# ---------------------------------------------------------------------------
# Merge real + simulated  &  apply year filter
# ---------------------------------------------------------------------------
df_monthly['es_simulado'] = False

if not df_simulated.empty:
    df_combined = pd.concat([df_monthly, df_simulated], ignore_index=True)
else:
    df_combined = df_monthly.copy()

df_combined = df_combined.sort_values('date_dt')

if selected_year != "Todos":
    df_view = df_combined[df_combined['year'] == selected_year].copy()
else:
    df_view = df_combined.copy()

df_view_real = df_view[~df_view['es_simulado']]
df_view_sim = df_view[df_view['es_simulado']]

# ---------------------------------------------------------------------------
# Summary Metrics
# ---------------------------------------------------------------------------
st.subheader("Resumen del Período")

# Row 1: Real totals
total_gen = df_view_real['yield_kwh'].sum()
total_saved = df_view_real['savings_clp'].sum()
total_avoided = df_view_real['avoided_cost_clp'].sum()

m1, m2, m3 = st.columns(3)
m1.metric("Energía Total Generada", f"{total_gen:,.1f} kWh")
m2.metric("Ahorro por Energía (CLP)", f"${total_saved:,.0f}")
m3.metric("Costo de Red Evitado (Est.)", f"${total_avoided:,.0f}", help="Incluye cargos fijos teóricos")

# Row 2: Projected totals (only when simulation is active and has data)
if sim_enabled and not df_view_sim.empty:
    st.markdown("##### 🔮 Proyección (Real + Estimado)")
    proj_gen = df_view['yield_kwh'].sum()
    proj_saved = df_view['savings_clp'].sum()
    proj_avoided = df_view['avoided_cost_clp'].sum()

    p1, p2, p3 = st.columns(3)
    p1.metric("Energía Proyectada", f"{proj_gen:,.1f} kWh",
              delta=f"+{proj_gen - total_gen:,.1f} kWh sim.")
    p2.metric("Ahorro Proyectado (CLP)", f"${proj_saved:,.0f}",
              delta=f"+${proj_saved - total_saved:,.0f} sim.")
    p3.metric("Costo Evitado Proyectado", f"${proj_avoided:,.0f}",
              delta=f"+${proj_avoided - total_avoided:,.0f} sim.")

    st.info(
        "Los valores marcados como 🔮 **Estimado** son proyecciones basadas en los kWh "
        "configurados en el panel de simulación. No corresponden a datos reales."
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    fig_bar = go.Figure()
    # Real bars
    if not df_view_real.empty:
        fig_bar.add_trace(go.Bar(
            x=df_view_real['date_str'],
            y=df_view_real['savings_clp'],
            name='Datos reales',
            marker_color='#4CAF50',
            text=df_view_real['savings_clp'].apply(lambda v: f"${v:,.0f}"),
            textposition='auto',
        ))
    # Simulated bars
    if not df_view_sim.empty:
        fig_bar.add_trace(go.Bar(
            x=df_view_sim['date_str'],
            y=df_view_sim['savings_clp'],
            name='🔮 Estimado',
            marker_color='#90A4AE',
            opacity=0.5,
            text=df_view_sim['savings_clp'].apply(lambda v: f"${v:,.0f}"),
            textposition='auto',
        ))
    fig_bar.update_layout(
        title='Ahorro Mensual (Solo Energía)',
        xaxis_title='Mes',
        yaxis_title='CLP',
        barmode='overlay',
        legend=dict(orientation='h', y=1.12),
    )
    st.plotly_chart(fig_bar, use_container_width=True, key="chart_savings")

with col_chart2:
    fig_comp = go.Figure()

    # Theoretical bill line (all months)
    fig_comp.add_trace(go.Scatter(
        x=df_view['date_str'],
        y=df_view['theoretical_bill_clp'],
        mode='lines+markers',
        name='Factura Teórica (Red)',
        line=dict(color='#F44336', width=3, dash='dash'),
    ))
    # Real generation bars
    if not df_view_real.empty:
        fig_comp.add_trace(go.Bar(
            x=df_view_real['date_str'],
            y=df_view_real['savings_clp'],
            name='Generación Solar',
            marker_color='#4CAF50',
        ))
    # Simulated generation bars
    if not df_view_sim.empty:
        fig_comp.add_trace(go.Bar(
            x=df_view_sim['date_str'],
            y=df_view_sim['savings_clp'],
            name='🔮 Estimado',
            marker_color='#90A4AE',
            opacity=0.5,
        ))
    fig_comp.update_layout(
        title="Comparativa: Solar vs Red",
        xaxis_title="Mes",
        yaxis_title="Costo (CLP)",
        barmode='overlay',
        legend=dict(orientation='h', y=1.12),
    )
    st.plotly_chart(fig_comp, use_container_width=True, key="chart_comparison")

# ---------------------------------------------------------------------------
# Detailed Table
# ---------------------------------------------------------------------------
st.subheader("Desglose Mensual")

df_table = df_view[['date_str', 'yield_kwh', 'savings_clp', 'savings_usd',
                     'theoretical_bill_clp', 'es_simulado']].copy()
df_table['Tipo'] = df_table['es_simulado'].map({False: '✅ Real', True: '🔮 Estimado'})
df_table = df_table.drop(columns=['es_simulado'])
df_table.columns = ['Mes', 'Generación (kWh)', 'Ahorro Variable (CLP)',
                     'Ahorro (USD)', 'Factura Evitada (CLP)', 'Tipo']

st.dataframe(
    df_table.style.format({
        'Generación (kWh)': '{:.1f}',
        'Ahorro Variable (CLP)': '${:,.0f}',
        'Ahorro (USD)': '${:,.2f}',
        'Factura Evitada (CLP)': '${:,.0f}'
    }),
    use_container_width=True
)
