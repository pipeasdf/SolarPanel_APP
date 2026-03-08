"""
CSV parser for Victron solar data files.

Handles parsing, validation, timezone conversion, and data transformation
for CSV files exported from Victron VE.Direct devices.
"""

import io
from datetime import datetime
from typing import Tuple, List, Dict, Optional, Union
import pandas as pd
import pytz
from dateutil import parser as date_parser

from .column_mapper import (
    map_columns, get_mapping_report, REQUIRED_COLUMNS, STANDARD_COLUMNS
)


# Default timezone for parsing
DEFAULT_TIMEZONE = 'America/Santiago'


def detect_encoding(file_content: bytes) -> str:
    """
    Detect file encoding from content.
    
    Args:
        file_content: Raw file bytes
        
    Returns:
        Detected encoding string
    """
    # Try common encodings
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            file_content.decode(encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue
    
    return 'utf-8'  # Default fallback


def detect_delimiter(content: str) -> str:
    """
    Detect CSV delimiter from content.
    
    Args:
        content: File content as string
        
    Returns:
        Detected delimiter character
    """
    # Get first few lines
    lines = content.split('\n')[:5]
    first_line = lines[0] if lines else ''
    
    # Count potential delimiters
    delimiters = {',': 0, ';': 0, '\t': 0, '|': 0}
    for delim in delimiters:
        delimiters[delim] = first_line.count(delim)
    
    # Return most common delimiter, default to comma
    best = max(delimiters, key=delimiters.get)
    return best if delimiters[best] > 0 else ','


def parse_date(date_str: str, timezone: str = DEFAULT_TIMEZONE) -> Optional[datetime]:
    """
    Parse a date string with timezone awareness.
    
    Supports various formats:
    - ISO format: 2024-01-15T10:30:00
    - American: 01-15-2024, 01/15/2024 (MM-DD-YYYY) - PRIMARY
    - European: 15/01/2024 10:30 (DD/MM/YYYY)
    - Date only: 2024-01-15
    
    Args:
        date_str: Date string to parse
        timezone: Target timezone
        
    Returns:
        Parsed datetime with timezone, or None if parsing fails
    """
    if pd.isna(date_str) or not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    try:
        # Try American format first (MM-DD-YYYY) - dayfirst=False
        parsed = date_parser.parse(date_str, dayfirst=False)
        
        # Add timezone if naive
        tz = pytz.timezone(timezone)
        if parsed.tzinfo is None:
            parsed = tz.localize(parsed)
        else:
            parsed = parsed.astimezone(tz)
        
        return parsed
        
    except (ValueError, TypeError):
        # Fallback: try European format (DD/MM/YYYY)
        try:
            parsed = date_parser.parse(date_str, dayfirst=True)
            tz = pytz.timezone(timezone)
            if parsed.tzinfo is None:
                parsed = tz.localize(parsed)
            else:
                parsed = parsed.astimezone(tz)
            return parsed
        except (ValueError, TypeError):
            return None


def parse_numeric(value: any, default: float = 0.0) -> float:
    """
    Parse a numeric value, handling various formats.
    
    Args:
        value: Value to parse
        default: Default if parsing fails
        
    Returns:
        Parsed float value
    """
    if pd.isna(value):
        return default
    
    if isinstance(value, (int, float)):
        return float(value)
    
    try:
        # Handle string with comma as decimal separator
        str_value = str(value).strip()
        str_value = str_value.replace(',', '.')
        str_value = str_value.replace(' ', '')
        return float(str_value)
    except (ValueError, TypeError):
        return default


def parse_csv(
    file_content: Union[bytes, str, io.IOBase],
    timezone: str = DEFAULT_TIMEZONE
) -> Tuple[pd.DataFrame, dict]:
    """
    Parse a Victron CSV file.
    
    Args:
        file_content: CSV content as bytes, string, or file-like object
        timezone: Timezone for date parsing
        
    Returns:
        Tuple of:
        - DataFrame with standardized columns
        - Validation report
    """
    # Handle different input types
    if isinstance(file_content, bytes):
        encoding = detect_encoding(file_content)
        content_str = file_content.decode(encoding)
    elif isinstance(file_content, str):
        content_str = file_content
    else:
        content_str = file_content.read()
        if isinstance(content_str, bytes):
            encoding = detect_encoding(content_str)
            content_str = content_str.decode(encoding)
    
    # Detect delimiter
    delimiter = detect_delimiter(content_str)
    
    # Read CSV
    df = pd.read_csv(
        io.StringIO(content_str),
        delimiter=delimiter,
        skipinitialspace=True
    )
    
    # Get column mapping
    report = get_mapping_report(list(df.columns))
    
    if not report['is_valid']:
        return pd.DataFrame(), report
    
    # Rename columns to standard names
    mapping = report['mapping']
    df = df.rename(columns=mapping)
    
    # Keep only mapped columns
    cols_to_keep = [col for col in df.columns if col in STANDARD_COLUMNS]
    df = df[cols_to_keep]
    
    # Parse and transform data
    df = transform_dataframe(df, timezone)
    
    # Update report with row counts
    report['row_count'] = len(df)
    report['valid_rows'] = len(df.dropna(subset=['timestamp']))
    
    return df, report


def transform_dataframe(df: pd.DataFrame, timezone: str = DEFAULT_TIMEZONE) -> pd.DataFrame:
    """
    Transform DataFrame to standard format.
    
    - Parse dates with timezone
    - Convert numeric columns
    - Handle missing values
    
    Args:
        df: Input DataFrame with standard column names
        timezone: Timezone for dates
        
    Returns:
        Transformed DataFrame
    """
    result = df.copy()
    
    # Parse timestamps
    if 'timestamp' in result.columns:
        result['timestamp'] = result['timestamp'].apply(
            lambda x: parse_date(x, timezone)
        )
    
    # Parse numeric columns
    numeric_columns = [
        'yield_wh', 'min_voltage', 'max_voltage',
        'bulk_m', 'absorption_m', 'float_m',
        'pv_power_max', 'pv_voltage_max'
    ]
    
    for col in numeric_columns:
        if col in result.columns:
            result[col] = result[col].apply(parse_numeric)
    
    # Integer columns (times in minutes)
    int_columns = ['bulk_m', 'absorption_m', 'float_m']
    for col in int_columns:
        if col in result.columns:
            result[col] = result[col].fillna(0).astype(int)
    
    # Handle error_text - keep as string
    if 'error_text' in result.columns:
        result['error_text'] = result['error_text'].fillna('').astype(str)
        result['error_text'] = result['error_text'].replace('nan', '')
    
    # Add missing optional columns with defaults
    for col in ['bulk_m', 'absorption_m', 'float_m']:
        if col not in result.columns:
            result[col] = 0
    
    for col in ['pv_power_max', 'pv_voltage_max']:
        if col not in result.columns:
            result[col] = None
    
    if 'error_text' not in result.columns:
        result['error_text'] = ''
    
    return result


def validate_dataframe(df: pd.DataFrame) -> dict:
    """
    Validate a parsed DataFrame.
    
    Checks:
    - Required columns present
    - No null timestamps
    - Voltage values in valid range
    - No duplicate dates
    
    Args:
        df: DataFrame to validate
        
    Returns:
        Validation report dictionary
    """
    issues = []
    warnings = []
    
    # Check required columns
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            issues.append(f"Missing required column: {col}")
    
    if issues:
        return {
            'is_valid': False,
            'issues': issues,
            'warnings': warnings,
            'row_count': len(df),
            'valid_rows': 0
        }
    
    # Check for null timestamps
    null_timestamps = df['timestamp'].isna().sum()
    if null_timestamps > 0:
        warnings.append(f"{null_timestamps} rows have invalid/missing timestamps")
    
    # Check voltage ranges (should be 0-100V for a 48V system)
    if 'min_voltage' in df.columns:
        invalid_min = ((df['min_voltage'] < 0) | (df['min_voltage'] > 100)).sum()
        if invalid_min > 0:
            warnings.append(f"{invalid_min} rows have min_voltage outside 0-100V range")
    
    if 'max_voltage' in df.columns:
        invalid_max = ((df['max_voltage'] < 0) | (df['max_voltage'] > 100)).sum()
        if invalid_max > 0:
            warnings.append(f"{invalid_max} rows have max_voltage outside 0-100V range")
    
    # Check for duplicates
    if 'timestamp' in df.columns:
        valid_timestamps = df.dropna(subset=['timestamp'])
        duplicates = valid_timestamps['timestamp'].duplicated().sum()
        if duplicates > 0:
            warnings.append(f"{duplicates} duplicate timestamps found")
    
    # Check yield values
    if 'yield_wh' in df.columns:
        negative_yield = (df['yield_wh'] < 0).sum()
        if negative_yield > 0:
            warnings.append(f"{negative_yield} rows have negative yield values")
    
    valid_rows = len(df.dropna(subset=['timestamp', 'yield_wh', 'min_voltage', 'max_voltage']))
    
    return {
        'is_valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'row_count': len(df),
        'valid_rows': valid_rows
    }


def preview_csv(
    file_content: Union[bytes, str, io.IOBase],
    max_rows: int = 10
) -> Tuple[pd.DataFrame, dict]:
    """
    Preview a CSV file without full processing.
    
    Args:
        file_content: CSV content
        max_rows: Maximum rows to show in preview
        
    Returns:
        Tuple of preview DataFrame and column mapping report
    """
    # Handle different input types
    if isinstance(file_content, bytes):
        encoding = detect_encoding(file_content)
        content_str = file_content.decode(encoding)
    elif isinstance(file_content, str):
        content_str = file_content
    else:
        content_str = file_content.read()
        if isinstance(content_str, bytes):
            encoding = detect_encoding(content_str)
            content_str = content_str.decode(encoding)
    
    delimiter = detect_delimiter(content_str)
    
    # Read just first few rows
    df = pd.read_csv(
        io.StringIO(content_str),
        delimiter=delimiter,
        skipinitialspace=True,
        nrows=max_rows
    )
    
    # Get mapping report
    report = get_mapping_report(list(df.columns))
    
    return df, report
