"""
Column mapping for Victron CSV files.

Handles flexible column name recognition for various CSV export formats
from Victron VE.Direct, MPPT controllers, and inverters.
"""

from typing import Dict, List, Optional, Tuple
import re


# Standard column names used internally
STANDARD_COLUMNS = [
    'timestamp',
    'yield_wh',
    'min_voltage',
    'max_voltage',
    'bulk_m',
    'absorption_m',
    'float_m',
    'pv_power_max',
    'pv_voltage_max',
    'error_text'
]

# Required columns (must be present for valid import)
REQUIRED_COLUMNS = ['timestamp', 'yield_wh', 'min_voltage', 'max_voltage']

# Optional columns (nice to have)
OPTIONAL_COLUMNS = ['bulk_m', 'absorption_m', 'float_m', 'pv_power_max', 'pv_voltage_max', 'error_text']


# Column mapping: standard_name -> list of alternative names (case-insensitive patterns)
COLUMN_MAPPINGS: Dict[str, List[str]] = {
    'timestamp': [
        'date', 'timestamp', 'fecha', 'datetime', 'time', 'fecha/hora',
        'date/time', 'fechahora', 'registro'
    ],
    'yield_wh': [
        'yield(wh)', 'yield (wh)', 'yield_wh', 'producción', 'produccion',
        'energy', 'energia', 'energía', 'yield wh', 'yield', 'energy(wh)',
        'daily yield', 'rendimiento', 'wh', 'producción (wh)', 'produccion (wh)'
    ],
    'min_voltage': [
        'min. battery voltage(v)', 'min battery voltage(v)', 'min. battery voltage (v)',
        'min battery voltage', 'min voltage', 'vmin', 'v_min', 'minvoltage',
        'minimum voltage', 'voltaje mínimo', 'voltaje minimo', 'min_voltage',
        'battery min', 'bat min v', 'min v'
    ],
    'max_voltage': [
        'max. battery voltage(v)', 'max battery voltage(v)', 'max. battery voltage (v)',
        'max battery voltage', 'max voltage', 'vmax', 'v_max', 'maxvoltage',
        'maximum voltage', 'voltaje máximo', 'voltaje maximo', 'max_voltage',
        'battery max', 'bat max v', 'max v'
    ],
    'bulk_m': [
        'time in bulk(m)', 'time in bulk (m)', 'time in bulk', 'bulk (m)',
        'bulk_minutes', 'bulk_m', 'bulk', 'tiempo bulk', 'tiempo en bulk',
        'bulk time', 'bulk min', 'bulkm'
    ],
    'absorption_m': [
        'time in absorption(m)', 'time in absorption (m)', 'time in absorption',
        'absorption (m)', 'abs_minutes', 'absorption_m', 'absorption',
        'tiempo absorción', 'tiempo absorcion', 'tiempo en absorcion',
        'absorption time', 'abs min', 'absm', 'abs', 'absorción'
    ],
    'float_m': [
        'time in float(m)', 'time in float (m)', 'time in float', 'float (m)',
        'float_minutes', 'float_m', 'float', 'tiempo flotación', 'tiempo flotacion',
        'tiempo en flotacion', 'float time', 'float min', 'floatm', 'flotación', 'flotacion'
    ],
    'pv_power_max': [
        'max pv power (w)', 'max pv power(w)', 'max pv power', 'pv power max',
        'max power', 'potencia máxima', 'potencia maxima', 'pv_power_max',
        'max power w', 'pv max power', 'power max', 'maxpower',
        'max. pv power(w)', 'max. pv power (w)', 'max. pv power', 'max. power'
    ],
    'pv_voltage_max': [
        'max pv voltage (v)', 'max pv voltage(v)', 'max pv voltage', 'pv voltage max',
        'max pv v', 'voltaje pv máximo', 'voltaje pv maximo', 'pv_voltage_max',
        'pv max voltage', 'vpv max', 'max vpv',
        'max. pv voltage(v)', 'max. pv voltage (v)', 'max. pv voltage', 'max. voltage'
    ],
    'error_text': [
        'errors', 'lasterror', 'last error', 'error', 'error_code', 'errores',
        'error_text', 'fault', 'faults', 'alarm', 'alarms', 'warning'
    ]
}


def normalize_column_name(name: str) -> str:
    """
    Normalize a column name for matching.
    
    - Lowercase
    - Strip whitespace
    - Remove extra spaces
    
    Args:
        name: Original column name
        
    Returns:
        Normalized column name
    """
    normalized = name.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def find_standard_column(column_name: str) -> Optional[str]:
    """
    Find the standard column name for a given CSV column.
    
    Args:
        column_name: Column name from CSV
        
    Returns:
        Standard column name if matched, None otherwise
    """
    normalized = normalize_column_name(column_name)
    
    for standard_name, alternatives in COLUMN_MAPPINGS.items():
        # Check if it matches any alternative
        for alt in alternatives:
            if normalize_column_name(alt) == normalized:
                return standard_name
    
    return None


def map_columns(csv_columns: List[str]) -> Tuple[Dict[str, str], List[str], List[str]]:
    """
    Map CSV columns to standard column names.
    
    Args:
        csv_columns: List of column names from CSV header
        
    Returns:
        Tuple of:
        - mapping: Dict of csv_column -> standard_column
        - unmapped: List of CSV columns that couldn't be mapped
        - missing_required: List of required standard columns not found
    """
    mapping = {}
    unmapped = []
    found_standard = set()
    
    for csv_col in csv_columns:
        standard = find_standard_column(csv_col)
        if standard:
            mapping[csv_col] = standard
            found_standard.add(standard)
        else:
            unmapped.append(csv_col)
    
    # Check for missing required columns
    missing_required = [col for col in REQUIRED_COLUMNS if col not in found_standard]
    
    return mapping, unmapped, missing_required


def get_mapping_report(csv_columns: List[str]) -> dict:
    """
    Generate a detailed mapping report for CSV columns.
    
    Args:
        csv_columns: List of column names from CSV header
        
    Returns:
        Report dictionary with mapping details
    """
    mapping, unmapped, missing_required = map_columns(csv_columns)
    
    # Find which optional columns are present
    found_standard = set(mapping.values())
    missing_optional = [col for col in OPTIONAL_COLUMNS if col not in found_standard]
    
    return {
        'mapping': mapping,
        'unmapped_columns': unmapped,
        'missing_required': missing_required,
        'missing_optional': missing_optional,
        'is_valid': len(missing_required) == 0,
        'total_columns': len(csv_columns),
        'mapped_columns': len(mapping),
        'required_found': len(REQUIRED_COLUMNS) - len(missing_required),
        'required_total': len(REQUIRED_COLUMNS)
    }
