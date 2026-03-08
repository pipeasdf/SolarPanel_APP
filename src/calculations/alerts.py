"""
Alert detection for solar panel monitoring.

Detects various issues and anomalies in the solar system data:
- Deep discharge events
- Missing absorption/float charging phases
- Error conditions
- Voltage anomalies
"""

from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


class AlertType(Enum):
    """Types of alerts that can be detected."""
    DEEP_DISCHARGE = 'deep_discharge'
    CRITICAL_DISCHARGE = 'critical_discharge'
    NEAR_CUTOFF = 'near_cutoff'
    NO_ABSORPTION = 'no_absorption'
    NO_FLOAT = 'no_float'
    ERROR_DETECTED = 'error_detected'
    LOW_YIELD = 'low_yield'
    VOLTAGE_ANOMALY = 'voltage_anomaly'


class Severity(Enum):
    """Alert severity levels."""
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'


@dataclass
class AlertInfo:
    """Information about a detected alert."""
    alert_type: AlertType
    severity: Severity
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None


# Default thresholds
DEFAULT_THRESHOLDS = {
    'v_warning': 44.0,      # Deep discharge warning
    'v_critical': 42.0,     # Critical discharge
    'v_near_cutoff': 40.0,  # Near cutoff
    'v_cutoff': 37.5,       # System cutoff
    'min_yield_wh': 100,    # Minimum expected yield (Wh)
}


def detect_voltage_alerts(
    min_voltage: float,
    thresholds: dict = None
) -> List[AlertInfo]:
    """
    Detect voltage-related alerts.
    
    Args:
        min_voltage: Minimum voltage recorded for the day
        thresholds: Custom thresholds (optional)
        
    Returns:
        List of detected alerts
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS
    
    alerts = []
    
    if min_voltage is None:
        return alerts
    
    v_warning = thresholds.get('v_warning', 44.0)
    v_critical = thresholds.get('v_critical', 42.0)
    v_near_cutoff = thresholds.get('v_near_cutoff', 40.0)
    
    # Check for near cutoff (most severe)
    if min_voltage < v_near_cutoff:
        alerts.append(AlertInfo(
            alert_type=AlertType.NEAR_CUTOFF,
            severity=Severity.CRITICAL,
            message=f'Voltaje muy bajo cercano al corte: {min_voltage:.1f}V (umbral: {v_near_cutoff}V)',
            value=min_voltage,
            threshold=v_near_cutoff
        ))
    # Check for critical discharge
    elif min_voltage < v_critical:
        alerts.append(AlertInfo(
            alert_type=AlertType.CRITICAL_DISCHARGE,
            severity=Severity.CRITICAL,
            message=f'Descarga crítica detectada: {min_voltage:.1f}V (umbral: {v_critical}V)',
            value=min_voltage,
            threshold=v_critical
        ))
    # Check for deep discharge warning
    elif min_voltage < v_warning:
        alerts.append(AlertInfo(
            alert_type=AlertType.DEEP_DISCHARGE,
            severity=Severity.WARNING,
            message=f'Descarga profunda: {min_voltage:.1f}V (umbral: {v_warning}V)',
            value=min_voltage,
            threshold=v_warning
        ))
    
    return alerts


def detect_charging_alerts(
    absorption_m: int,
    float_m: int
) -> List[AlertInfo]:
    """
    Detect charging phase alerts.
    
    Args:
        absorption_m: Time in absorption phase (minutes)
        float_m: Time in float phase (minutes)
        
    Returns:
        List of detected alerts
    """
    alerts = []
    
    # Check for no absorption
    if absorption_m is not None and absorption_m == 0:
        alerts.append(AlertInfo(
            alert_type=AlertType.NO_ABSORPTION,
            severity=Severity.WARNING,
            message='Sin fase de absorción - las baterías no se cargaron completamente',
            value=absorption_m,
            threshold=1
        ))
    
    # Check for no float
    if float_m is not None and float_m == 0:
        alerts.append(AlertInfo(
            alert_type=AlertType.NO_FLOAT,
            severity=Severity.INFO,
            message='Sin fase de flotación - carga incompleta o consumo alto',
            value=float_m,
            threshold=1
        ))
    
    return alerts


def detect_error_alerts(error_text: str) -> List[AlertInfo]:
    """
    Detect error-related alerts.
    
    Args:
        error_text: Error text from Victron device
        
    Returns:
        List of detected alerts
    """
    alerts = []
    
    if error_text and error_text.strip() and error_text.lower() not in ['', 'none', 'nan', '0']:
        alerts.append(AlertInfo(
            alert_type=AlertType.ERROR_DETECTED,
            severity=Severity.WARNING,
            message=f'Error del dispositivo: {error_text}',
            value=None,
            threshold=None
        ))
    
    return alerts


def detect_yield_alerts(
    yield_wh: float,
    min_yield: float = None
) -> List[AlertInfo]:
    """
    Detect yield-related alerts.
    
    Args:
        yield_wh: Daily yield in Wh
        min_yield: Minimum expected yield (optional)
        
    Returns:
        List of detected alerts
    """
    alerts = []
    
    if min_yield is None:
        min_yield = DEFAULT_THRESHOLDS['min_yield_wh']
    
    if yield_wh is not None and yield_wh < min_yield:
        alerts.append(AlertInfo(
            alert_type=AlertType.LOW_YIELD,
            severity=Severity.INFO,
            message=f'Producción baja: {yield_wh:.0f}Wh (esperado: >{min_yield:.0f}Wh)',
            value=yield_wh,
            threshold=min_yield
        ))
    
    return alerts


def detect_alerts(
    min_voltage: float = None,
    max_voltage: float = None,
    absorption_m: int = None,
    float_m: int = None,
    error_text: str = None,
    yield_wh: float = None,
    thresholds: dict = None
) -> List[AlertInfo]:
    """
    Detect all alerts for a single record.
    
    Args:
        min_voltage: Minimum voltage for the day
        max_voltage: Maximum voltage for the day
        absorption_m: Time in absorption (minutes)
        float_m: Time in float (minutes)
        error_text: Error text
        yield_wh: Daily yield (Wh)
        thresholds: Custom thresholds
        
    Returns:
        List of all detected alerts
    """
    all_alerts = []
    
    # Voltage alerts
    if min_voltage is not None:
        all_alerts.extend(detect_voltage_alerts(min_voltage, thresholds))
    
    # Charging alerts
    all_alerts.extend(detect_charging_alerts(absorption_m or 0, float_m or 0))
    
    # Error alerts
    all_alerts.extend(detect_error_alerts(error_text or ''))
    
    # Yield alerts (optional)
    if yield_wh is not None:
        all_alerts.extend(detect_yield_alerts(yield_wh))
    
    return all_alerts


def get_alert_summary(alerts: List[AlertInfo]) -> dict:
    """
    Get summary statistics for a list of alerts.
    
    Args:
        alerts: List of alerts
        
    Returns:
        Summary dictionary
    """
    summary = {
        'total': len(alerts),
        'critical': 0,
        'warning': 0,
        'info': 0,
        'by_type': {}
    }
    
    for alert in alerts:
        # Count by severity
        if alert.severity == Severity.CRITICAL:
            summary['critical'] += 1
        elif alert.severity == Severity.WARNING:
            summary['warning'] += 1
        else:
            summary['info'] += 1
        
        # Count by type
        type_name = alert.alert_type.value
        summary['by_type'][type_name] = summary['by_type'].get(type_name, 0) + 1
    
    return summary


def get_severity_color(severity: Severity) -> str:
    """Get color for a severity level."""
    colors = {
        Severity.CRITICAL: '#F44336',  # Red
        Severity.WARNING: '#FFC107',   # Amber
        Severity.INFO: '#2196F3'       # Blue
    }
    return colors.get(severity, '#9E9E9E')


def get_severity_icon(severity: Severity) -> str:
    """Get emoji icon for a severity level."""
    icons = {
        Severity.CRITICAL: '🔴',
        Severity.WARNING: '🟡',
        Severity.INFO: 'ℹ️'
    }
    return icons.get(severity, '⚪')


def format_alert_message(alert: AlertInfo) -> str:
    """Format alert for display."""
    icon = get_severity_icon(alert.severity)
    return f"{icon} {alert.message}"
