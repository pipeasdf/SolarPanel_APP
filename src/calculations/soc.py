"""
State of Charge (SOC) calculations for 48V battery bank.

Uses linear interpolation between cutoff voltage and full voltage.
Default values based on NARADA MPG12V200 specifications:
- V_full_pack (100%): 56.4V (4 × 14.1V float = 4 × 6 cells × 2.35Vpc)
- V_cutoff (0%): 37.5V (system cutoff)
"""

from typing import Optional, Tuple


# Default voltage thresholds
DEFAULT_V_FULL = 56.4  # Full pack voltage at 100% SOC
DEFAULT_V_CUTOFF = 37.5  # Cutoff voltage at 0% SOC
DEFAULT_BATTERY_COUNT = 4  # Number of batteries in series


def calculate_soc(
    voltage: float,
    v_full: float = DEFAULT_V_FULL,
    v_cutoff: float = DEFAULT_V_CUTOFF
) -> float:
    """
    Calculate State of Charge (SOC) using linear interpolation.
    
    Formula:
        SOC% = clip((V_measured - V_cutoff) / (V_full - V_cutoff) * 100, 0, 100)
    
    Args:
        voltage: Measured battery pack voltage (V)
        v_full: Full pack voltage at 100% SOC (default: 56.4V)
        v_cutoff: Cutoff voltage at 0% SOC (default: 37.5V)
        
    Returns:
        SOC percentage (0-100)
        
    Note:
        This is a linear approximation. Actual SOC depends on many factors
        including temperature, discharge rate, and battery age.
    """
    if v_full <= v_cutoff:
        raise ValueError("v_full must be greater than v_cutoff")
    
    if voltage is None or voltage <= 0:
        return 0.0
    
    soc = (voltage - v_cutoff) / (v_full - v_cutoff) * 100
    
    # Clamp to 0-100 range
    return max(0.0, min(100.0, soc))


def calculate_soc_per_battery(
    pack_voltage: float,
    battery_count: int = DEFAULT_BATTERY_COUNT
) -> float:
    """
    Calculate individual battery voltage from pack voltage.
    
    For batteries in series, pack voltage = sum of individual voltages.
    
    Args:
        pack_voltage: Total pack voltage (V)
        battery_count: Number of batteries in series (default: 4)
        
    Returns:
        Individual battery voltage (V)
    """
    if battery_count <= 0:
        raise ValueError("battery_count must be positive")
    
    if pack_voltage is None or pack_voltage <= 0:
        return 0.0
    
    return pack_voltage / battery_count


def get_soc_category(soc: float) -> Tuple[str, str]:
    """
    Get SOC category and color for display.
    
    Categories:
    - Excellent: 80-100% (green)
    - Good: 60-80% (light green)
    - Moderate: 40-60% (yellow)
    - Low: 20-40% (orange)
    - Critical: 0-20% (red)
    
    Args:
        soc: SOC percentage (0-100)
        
    Returns:
        Tuple of (category_name, color_hex)
    """
    if soc >= 80:
        return ('Excelente', '#4CAF50')  # Green
    elif soc >= 60:
        return ('Bueno', '#8BC34A')  # Light green
    elif soc >= 40:
        return ('Moderado', '#FFC107')  # Amber/Yellow
    elif soc >= 20:
        return ('Bajo', '#FF9800')  # Orange
    else:
        return ('Crítico', '#F44336')  # Red


def estimate_remaining_capacity(
    soc: float,
    total_capacity_ah: float = 200.0
) -> float:
    """
    Estimate remaining battery capacity.
    
    Args:
        soc: Current SOC percentage
        total_capacity_ah: Total battery capacity in Ah (default: 200Ah)
        
    Returns:
        Estimated remaining capacity in Ah
    """
    return (soc / 100.0) * total_capacity_ah


def calculate_voltage_from_soc(
    soc: float,
    v_full: float = DEFAULT_V_FULL,
    v_cutoff: float = DEFAULT_V_CUTOFF
) -> float:
    """
    Calculate expected voltage from SOC (inverse of calculate_soc).
    
    Args:
        soc: SOC percentage (0-100)
        v_full: Full pack voltage at 100% SOC
        v_cutoff: Cutoff voltage at 0% SOC
        
    Returns:
        Expected voltage (V)
    """
    soc_clamped = max(0.0, min(100.0, soc))
    voltage = v_cutoff + (soc_clamped / 100.0) * (v_full - v_cutoff)
    return voltage


def get_voltage_reference_lines(
    v_full: float = DEFAULT_V_FULL,
    v_cutoff: float = DEFAULT_V_CUTOFF,
    v_warning: float = 44.0,
    v_critical: float = 42.0
) -> dict:
    """
    Get voltage reference lines for charts.
    
    Args:
        v_full: Full voltage threshold
        v_cutoff: Cutoff voltage threshold
        v_warning: Warning voltage threshold
        v_critical: Critical voltage threshold
        
    Returns:
        Dictionary with reference line definitions
    """
    return {
        'v_full': {
            'value': v_full,
            'label': f'100% SOC ({v_full}V)',
            'color': '#4CAF50',
            'dash': 'dash'
        },
        'v_warning': {
            'value': v_warning,
            'label': f'Warning ({v_warning}V)',
            'color': '#FFC107',
            'dash': 'dot'
        },
        'v_critical': {
            'value': v_critical,
            'label': f'Critical ({v_critical}V)',
            'color': '#FF9800',
            'dash': 'dot'
        },
        'v_cutoff': {
            'value': v_cutoff,
            'label': f'Cutoff ({v_cutoff}V)',
            'color': '#F44336',
            'dash': 'solid'
        }
    }


def analyze_soc_trend(soc_values: list) -> dict:
    """
    Analyze SOC trend over time.
    
    Args:
        soc_values: List of SOC values (chronological order)
        
    Returns:
        Analysis dictionary with trend information
    """
    if not soc_values or len(soc_values) < 2:
        return {
            'trend': 'insufficient_data',
            'average': soc_values[0] if soc_values else 0,
            'min': soc_values[0] if soc_values else 0,
            'max': soc_values[0] if soc_values else 0,
            'change': 0
        }
    
    # Calculate statistics
    avg_soc = sum(soc_values) / len(soc_values)
    min_soc = min(soc_values)
    max_soc = max(soc_values)
    
    # Calculate trend (comparing first half to second half)
    mid = len(soc_values) // 2
    first_half_avg = sum(soc_values[:mid]) / mid if mid > 0 else 0
    second_half_avg = sum(soc_values[mid:]) / (len(soc_values) - mid)
    
    change = second_half_avg - first_half_avg
    
    if change > 5:
        trend = 'improving'
    elif change < -5:
        trend = 'declining'
    else:
        trend = 'stable'
    
    return {
        'trend': trend,
        'average': round(avg_soc, 1),
        'min': round(min_soc, 1),
        'max': round(max_soc, 1),
        'change': round(change, 1),
        'days_critical': sum(1 for s in soc_values if s < 20),
        'days_low': sum(1 for s in soc_values if 20 <= s < 40),
        'days_good': sum(1 for s in soc_values if s >= 60)
    }
