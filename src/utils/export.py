"""
Export utilities for CSV and Excel formats.

Provides functions to export data and reports in various formats.
"""

import io
from datetime import datetime
from typing import Optional, List
import pandas as pd


def export_to_csv(
    df: pd.DataFrame,
    filename: Optional[str] = None,
    include_index: bool = False
) -> io.BytesIO:
    """
    Export DataFrame to CSV.
    
    Args:
        df: DataFrame to export
        filename: Optional filename (not used, returns buffer)
        include_index: Whether to include the index
        
    Returns:
        BytesIO buffer with CSV content
    """
    buffer = io.BytesIO()
    
    # Format datetime columns
    df_export = df.copy()
    for col in df_export.columns:
        if pd.api.types.is_datetime64_any_dtype(df_export[col]):
            df_export[col] = df_export[col].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    df_export.to_csv(buffer, index=include_index, encoding='utf-8-sig')
    buffer.seek(0)
    
    return buffer


def export_to_excel(
    df: pd.DataFrame,
    filename: Optional[str] = None,
    sheet_name: str = 'Data',
    include_index: bool = False,
    additional_sheets: Optional[dict] = None
) -> io.BytesIO:
    """
    Export DataFrame to Excel with formatting.
    
    Args:
        df: Main DataFrame to export
        filename: Optional filename (not used, returns buffer)
        sheet_name: Name of the main sheet
        include_index: Whether to include the index
        additional_sheets: Dict of {sheet_name: DataFrame} for additional sheets
        
    Returns:
        BytesIO buffer with Excel content
    """
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Write main sheet
        df.to_excel(writer, sheet_name=sheet_name, index=include_index)
        
        # Auto-adjust column widths
        worksheet = writer.sheets[sheet_name]
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).str.len().max(),
                len(str(col))
            ) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
        
        # Write additional sheets
        if additional_sheets:
            for name, data in additional_sheets.items():
                data.to_excel(writer, sheet_name=name, index=include_index)
    
    buffer.seek(0)
    return buffer


def format_dataframe_for_export(
    df: pd.DataFrame,
    columns_to_include: Optional[List[str]] = None,
    column_labels: Optional[dict] = None,
    date_format: str = '%Y-%m-%d'
) -> pd.DataFrame:
    """
    Format a DataFrame for export with friendly column names.
    
    Args:
        df: Source DataFrame
        columns_to_include: List of columns to include (None = all)
        column_labels: Dict mapping column names to labels
        date_format: Format string for dates
        
    Returns:
        Formatted DataFrame
    """
    # Default column labels (Spanish)
    default_labels = {
        'timestamp': 'Fecha',
        'yield_wh': 'Producción (Wh)',
        'min_voltage': 'Voltaje Mín (V)',
        'max_voltage': 'Voltaje Máx (V)',
        'bulk_m': 'Bulk (min)',
        'absorption_m': 'Absorción (min)',
        'float_m': 'Flotación (min)',
        'pv_power_max': 'Potencia PV Máx (W)',
        'pv_voltage_max': 'Voltaje PV Máx (V)',
        'error_text': 'Errores',
        'soc': 'SOC (%)',
        'date': 'Fecha',
        'is_deep_discharge': 'Descarga Profunda',
        'alert_count': 'Alertas'
    }
    
    labels = {**default_labels, **(column_labels or {})}
    
    # Select columns
    if columns_to_include:
        df = df[[col for col in columns_to_include if col in df.columns]]
    
    # Format dates
    result = df.copy()
    for col in result.columns:
        if pd.api.types.is_datetime64_any_dtype(result[col]):
            result[col] = result[col].dt.strftime(date_format)
    
    # Rename columns
    result = result.rename(columns=labels)
    
    return result


def generate_report_summary(
    kpis,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Generate a summary DataFrame from KPIs for export.
    
    Args:
        kpis: KPIs dataclass
        period_start: Start of period
        period_end: End of period
        
    Returns:
        DataFrame with summary metrics
    """
    data = {
        'Métrica': [
            'Período',
            'Total días',
            'Producción total (kWh)',
            'Promedio diario (Wh)',
            'SOC promedio (%)',
            'SOC mínimo (%)',
            'SOC máximo (%)',
            'Días descarga profunda',
            'Días descarga crítica',
            'Días sin absorción',
            'Total alertas',
            'Último error'
        ],
        'Valor': [
            f"{kpis.period_start or period_start} a {kpis.period_end or period_end}",
            kpis.total_days,
            f"{kpis.total_yield_kwh:.2f}",
            f"{kpis.average_daily_yield_wh:.1f}",
            f"{kpis.average_soc:.1f}",
            f"{kpis.min_soc:.1f}",
            f"{kpis.max_soc:.1f}",
            kpis.days_deep_discharge,
            kpis.days_critical_discharge,
            kpis.days_no_absorption,
            kpis.total_alerts,
            kpis.last_error or 'Ninguno'
        ]
    }
    
    return pd.DataFrame(data)
