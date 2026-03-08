"""
Data aggregation and KPI calculations for solar monitoring.

Provides functions to calculate:
- Daily, weekly, monthly statistics
- Key Performance Indicators (KPIs)
- Comparison metrics between periods
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import pandas as pd

from .soc import calculate_soc, DEFAULT_V_FULL, DEFAULT_V_CUTOFF


@dataclass
class KPIs:
    """Key Performance Indicators for a period."""
    total_yield_kwh: float
    average_daily_yield_wh: float
    average_soc: float
    min_soc: float
    max_soc: float
    days_deep_discharge: int
    days_critical_discharge: int
    days_no_absorption: int
    total_days: int
    total_alerts: int
    last_error: Optional[str]
    period_start: Optional[date]
    period_end: Optional[date]


def calculate_kpis(
    df: pd.DataFrame,
    v_full: float = DEFAULT_V_FULL,
    v_cutoff: float = DEFAULT_V_CUTOFF,
    v_warning: float = 44.0,
    v_critical: float = 42.0
) -> KPIs:
    """
    Calculate KPIs from a DataFrame of records.
    
    Args:
        df: DataFrame with columns: timestamp, yield_wh, min_voltage, max_voltage,
            bulk_m, absorption_m, float_m, error_text
        v_full: Full voltage for SOC calculation
        v_cutoff: Cutoff voltage for SOC calculation
        v_warning: Warning threshold
        v_critical: Critical threshold
        
    Returns:
        KPIs dataclass with calculated metrics
    """
    if df.empty:
        return KPIs(
            total_yield_kwh=0,
            average_daily_yield_wh=0,
            average_soc=0,
            min_soc=0,
            max_soc=0,
            days_deep_discharge=0,
            days_critical_discharge=0,
            days_no_absorption=0,
            total_days=0,
            total_alerts=0,
            last_error=None,
            period_start=None,
            period_end=None
        )
    
    # Calculate SOC for each row
    df = df.copy()
    df['soc'] = df['min_voltage'].apply(
        lambda v: calculate_soc(v, v_full, v_cutoff) if pd.notna(v) else 0
    )
    
    # Total yield in kWh
    total_yield_kwh = df['yield_wh'].sum() / 1000
    
    # Average daily yield
    average_daily_yield_wh = df['yield_wh'].mean()
    
    # SOC statistics
    average_soc = df['soc'].mean()
    min_soc = df['soc'].min()
    max_soc = df['soc'].max()
    
    # Deep discharge days
    days_deep_discharge = (df['min_voltage'] < v_warning).sum()
    days_critical_discharge = (df['min_voltage'] < v_critical).sum()
    
    # Days without absorption
    if 'absorption_m' in df.columns:
        days_no_absorption = (df['absorption_m'] == 0).sum()
    else:
        days_no_absorption = 0
    
    # Total days
    total_days = len(df)
    
    # Total alerts (rough estimate based on conditions)
    total_alerts = days_deep_discharge + days_no_absorption
    
    # Last error
    last_error = None
    if 'error_text' in df.columns:
        errors = df[df['error_text'].notna() & (df['error_text'] != '')]
        if not errors.empty:
            last_error = errors.iloc[-1]['error_text']
    
    # Period dates
    period_start = None
    period_end = None
    if 'timestamp' in df.columns and not df['timestamp'].isna().all():
        valid_dates = df['timestamp'].dropna()
        if not valid_dates.empty:
            period_start = pd.to_datetime(valid_dates.min()).date()
            period_end = pd.to_datetime(valid_dates.max()).date()
    
    return KPIs(
        total_yield_kwh=round(total_yield_kwh, 2),
        average_daily_yield_wh=round(average_daily_yield_wh, 1),
        average_soc=round(average_soc, 1),
        min_soc=round(min_soc, 1),
        max_soc=round(max_soc, 1),
        days_deep_discharge=int(days_deep_discharge),
        days_critical_discharge=int(days_critical_discharge),
        days_no_absorption=int(days_no_absorption),
        total_days=total_days,
        total_alerts=total_alerts,
        last_error=last_error,
        period_start=period_start,
        period_end=period_end
    )


def calculate_monthly_stats(
    df: pd.DataFrame,
    v_full: float = DEFAULT_V_FULL,
    v_cutoff: float = DEFAULT_V_CUTOFF
) -> pd.DataFrame:
    """
    Calculate monthly statistics from daily records.
    
    Args:
        df: DataFrame with daily records
        v_full: Full voltage for SOC calculation
        v_cutoff: Cutoff voltage for SOC calculation
        
    Returns:
        DataFrame with monthly statistics
    """
    if df.empty or 'timestamp' not in df.columns:
        return pd.DataFrame()
    
    df = df.copy()
    
    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Add month column
    df['month'] = df['timestamp'].dt.to_period('M')
    
    # Calculate SOC
    df['soc'] = df['min_voltage'].apply(
        lambda v: calculate_soc(v, v_full, v_cutoff) if pd.notna(v) else 0
    )
    
    # Aggregate by month
    monthly = df.groupby('month').agg({
        'yield_wh': ['sum', 'mean', 'std'],
        'min_voltage': ['min', 'mean'],
        'max_voltage': ['max', 'mean'],
        'soc': ['mean', 'min', 'max'],
        'timestamp': 'count'
    }).reset_index()
    
    # Flatten column names
    monthly.columns = [
        'month',
        'total_yield_wh', 'avg_yield_wh', 'std_yield_wh',
        'min_voltage', 'avg_min_voltage',
        'max_voltage', 'avg_max_voltage',
        'avg_soc', 'min_soc', 'max_soc',
        'days_count'
    ]
    
    # Convert yield to kWh
    monthly['total_yield_kwh'] = monthly['total_yield_wh'] / 1000
    
    # Convert month to string
    monthly['month_str'] = monthly['month'].astype(str)
    
    return monthly


def compare_periods(
    df: pd.DataFrame,
    period1_start: date,
    period1_end: date,
    period2_start: date,
    period2_end: date,
    v_full: float = DEFAULT_V_FULL,
    v_cutoff: float = DEFAULT_V_CUTOFF
) -> dict:
    """
    Compare metrics between two periods.
    
    Args:
        df: DataFrame with all records
        period1_start: Start of first period
        period1_end: End of first period
        period2_start: Start of second period
        period2_end: End of second period
        v_full: Full voltage for SOC calculation
        v_cutoff: Cutoff voltage for SOC calculation
        
    Returns:
        Comparison dictionary with metrics for both periods and differences
    """
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    
    # Filter periods
    period1 = df[(df['date'] >= period1_start) & (df['date'] <= period1_end)]
    period2 = df[(df['date'] >= period2_start) & (df['date'] <= period2_end)]
    
    # Calculate KPIs for each period
    kpis1 = calculate_kpis(period1, v_full, v_cutoff)
    kpis2 = calculate_kpis(period2, v_full, v_cutoff)
    
    # Calculate differences
    def safe_diff(val1, val2):
        if val1 is None or val2 is None:
            return None
        return val2 - val1
    
    def safe_pct_change(val1, val2):
        if val1 is None or val2 is None or val1 == 0:
            return None
        return ((val2 - val1) / val1) * 100
    
    return {
        'period1': {
            'start': period1_start,
            'end': period1_end,
            'kpis': kpis1
        },
        'period2': {
            'start': period2_start,
            'end': period2_end,
            'kpis': kpis2
        },
        'differences': {
            'yield_kwh': safe_diff(kpis1.total_yield_kwh, kpis2.total_yield_kwh),
            'yield_pct': safe_pct_change(kpis1.total_yield_kwh, kpis2.total_yield_kwh),
            'avg_soc': safe_diff(kpis1.average_soc, kpis2.average_soc),
            'deep_discharge_days': safe_diff(kpis1.days_deep_discharge, kpis2.days_deep_discharge)
        }
    }


def get_daily_dataframe(
    df: pd.DataFrame,
    v_full: float = DEFAULT_V_FULL,
    v_cutoff: float = DEFAULT_V_CUTOFF,
    v_warning: float = 44.0
) -> pd.DataFrame:
    """
    Prepare daily DataFrame with SOC and alert flags for display.
    
    Args:
        df: Raw DataFrame with records
        v_full: Full voltage for SOC calculation
        v_cutoff: Cutoff voltage for SOC calculation
        v_warning: Warning threshold
        
    Returns:
        DataFrame ready for display with additional columns
    """
    if df.empty:
        return df
    
    result = df.copy()
    
    # Ensure timestamp is datetime
    if 'timestamp' in result.columns:
        result['timestamp'] = pd.to_datetime(result['timestamp'])
        result['date'] = result['timestamp'].dt.date
    
    # Calculate SOC
    result['soc'] = result['min_voltage'].apply(
        lambda v: calculate_soc(v, v_full, v_cutoff) if pd.notna(v) else 0
    )
    
    # Calculate per-battery voltage
    result['voltage_per_battery'] = result['min_voltage'] / 4
    
    # Add alert flags
    result['is_deep_discharge'] = result['min_voltage'] < v_warning
    
    if 'absorption_m' in result.columns:
        result['no_absorption'] = result['absorption_m'] == 0
    else:
        result['no_absorption'] = False
    
    if 'float_m' in result.columns:
        result['no_float'] = result['float_m'] == 0
    else:
        result['no_float'] = False
    
    # Count alerts per row
    alert_cols = ['is_deep_discharge', 'no_absorption', 'no_float']
    result['alert_count'] = result[alert_cols].sum(axis=1)
    
    return result


def generate_interpretation(kpis: KPIs, language: str = 'es') -> str:
    """
    Generate automatic interpretation text for KPIs.
    
    Args:
        kpis: Calculated KPIs
        language: Language code ('es' for Spanish, 'en' for English)
        
    Returns:
        Interpretation text
    """
    if kpis.total_days == 0:
        return "No hay datos suficientes para generar una interpretación."
    
    lines = []
    
    # Production summary
    lines.append(f"📊 **Resumen del período ({kpis.total_days} días)**")
    lines.append(f"- Producción total: {kpis.total_yield_kwh:.1f} kWh")
    lines.append(f"- Promedio diario: {kpis.average_daily_yield_wh:.0f} Wh")
    lines.append("")
    
    # SOC analysis
    lines.append("🔋 **Estado de carga (SOC)**")
    lines.append(f"- SOC promedio: {kpis.average_soc:.1f}%")
    lines.append(f"- Rango: {kpis.min_soc:.1f}% - {kpis.max_soc:.1f}%")
    
    # Deep discharge analysis
    if kpis.days_deep_discharge > 0:
        pct = (kpis.days_deep_discharge / kpis.total_days) * 100
        lines.append("")
        lines.append("⚠️ **Alertas de descarga**")
        lines.append(f"- Días con descarga profunda: {kpis.days_deep_discharge} ({pct:.1f}%)")
        
        if kpis.days_critical_discharge > 0:
            lines.append(f"- Días con descarga crítica: {kpis.days_critical_discharge}")
    
    # Recommendations
    lines.append("")
    lines.append("💡 **Recomendaciones**")
    
    if kpis.average_soc < 50:
        lines.append("- El SOC promedio es bajo. Considere reducir el consumo nocturno.")
    
    if kpis.days_deep_discharge > kpis.total_days * 0.3:
        lines.append("- Alta frecuencia de descargas profundas. Revise el consumo fantasma.")
    
    if kpis.days_no_absorption > kpis.total_days * 0.2:
        lines.append("- Frecuentes días sin absorción. Verifique los paneles y el MPPT.")
    
    if kpis.average_daily_yield_wh < 3000:  # Assuming 5kW system
        lines.append("- La producción diaria es baja. Considere limpiar los paneles.")
    
    if kpis.last_error:
        lines.append(f"- Último error registrado: {kpis.last_error}")
    
    if len(lines) == 8:  # No specific recommendations
        lines.append("- Sistema funcionando correctamente. Continúe el monitoreo regular.")
    
    return "\n".join(lines)
