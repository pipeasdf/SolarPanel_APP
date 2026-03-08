"""
Unit tests for alert detection.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.calculations.alerts import (
    detect_alerts, detect_voltage_alerts, detect_charging_alerts,
    detect_error_alerts, detect_yield_alerts, get_alert_summary,
    AlertType, Severity, AlertInfo
)


class TestVoltageAlerts:
    """Tests for voltage alert detection."""
    
    def test_no_alert_normal_voltage(self):
        """Test no alert for normal voltage."""
        alerts = detect_voltage_alerts(50.0)
        assert len(alerts) == 0
    
    def test_deep_discharge_warning(self):
        """Test deep discharge warning at 43V."""
        alerts = detect_voltage_alerts(43.0)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.DEEP_DISCHARGE
        assert alerts[0].severity == Severity.WARNING
    
    def test_critical_discharge(self):
        """Test critical discharge at 41V."""
        alerts = detect_voltage_alerts(41.0)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.CRITICAL_DISCHARGE
        assert alerts[0].severity == Severity.CRITICAL
    
    def test_near_cutoff(self):
        """Test near cutoff alert at 39V."""
        alerts = detect_voltage_alerts(39.0)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.NEAR_CUTOFF
        assert alerts[0].severity == Severity.CRITICAL
    
    def test_custom_thresholds(self):
        """Test with custom thresholds."""
        thresholds = {'v_warning': 48.0, 'v_critical': 46.0, 'v_near_cutoff': 44.0}
        
        # 47V should trigger warning with custom thresholds
        alerts = detect_voltage_alerts(47.0, thresholds)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.DEEP_DISCHARGE
    
    def test_none_voltage_no_alert(self):
        """Test that None voltage produces no alerts."""
        alerts = detect_voltage_alerts(None)
        assert len(alerts) == 0


class TestChargingAlerts:
    """Tests for charging phase alert detection."""
    
    def test_no_alert_normal_charging(self):
        """Test no alert with normal charging times."""
        alerts = detect_charging_alerts(absorption_m=60, float_m=120)
        assert len(alerts) == 0
    
    def test_no_absorption_alert(self):
        """Test alert when no absorption time."""
        alerts = detect_charging_alerts(absorption_m=0, float_m=120)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.NO_ABSORPTION
        assert alerts[0].severity == Severity.WARNING
    
    def test_no_float_alert(self):
        """Test alert when no float time."""
        alerts = detect_charging_alerts(absorption_m=60, float_m=0)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.NO_FLOAT
        assert alerts[0].severity == Severity.INFO
    
    def test_both_missing(self):
        """Test alerts when both absorption and float are zero."""
        alerts = detect_charging_alerts(absorption_m=0, float_m=0)
        assert len(alerts) == 2
        
        alert_types = [a.alert_type for a in alerts]
        assert AlertType.NO_ABSORPTION in alert_types
        assert AlertType.NO_FLOAT in alert_types


class TestErrorAlerts:
    """Tests for error detection."""
    
    def test_no_error_empty_text(self):
        """Test no alert with empty error text."""
        alerts = detect_error_alerts("")
        assert len(alerts) == 0
    
    def test_no_error_none(self):
        """Test no alert with None error text."""
        alerts = detect_error_alerts(None)
        assert len(alerts) == 0
    
    def test_no_error_nan(self):
        """Test no alert with 'nan' error text."""
        alerts = detect_error_alerts("nan")
        assert len(alerts) == 0
    
    def test_error_detected(self):
        """Test alert when error is present."""
        alerts = detect_error_alerts("Error: Low battery")
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.ERROR_DETECTED
        assert alerts[0].severity == Severity.WARNING
        assert "Low battery" in alerts[0].message


class TestYieldAlerts:
    """Tests for yield alert detection."""
    
    def test_no_alert_good_yield(self):
        """Test no alert with good yield."""
        alerts = detect_yield_alerts(5000)
        assert len(alerts) == 0
    
    def test_low_yield_alert(self):
        """Test alert with low yield."""
        alerts = detect_yield_alerts(50, min_yield=100)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.LOW_YIELD
        assert alerts[0].severity == Severity.INFO
    
    def test_none_yield_no_alert(self):
        """Test no alert with None yield."""
        alerts = detect_yield_alerts(None)
        assert len(alerts) == 0


class TestDetectAllAlerts:
    """Tests for combined alert detection."""
    
    def test_no_alerts_normal_data(self):
        """Test no alerts with normal data."""
        alerts = detect_alerts(
            min_voltage=50.0,
            max_voltage=56.0,
            absorption_m=60,
            float_m=120
        )
        assert len(alerts) == 0
    
    def test_multiple_alerts(self):
        """Test detection of multiple alerts."""
        alerts = detect_alerts(
            min_voltage=41.0,  # Critical discharge
            max_voltage=55.0,
            absorption_m=0,   # No absorption
            float_m=0,        # No float
            error_text="Error: Overload"
        )
        
        assert len(alerts) >= 4
        
        alert_types = [a.alert_type for a in alerts]
        assert AlertType.CRITICAL_DISCHARGE in alert_types
        assert AlertType.NO_ABSORPTION in alert_types
        assert AlertType.NO_FLOAT in alert_types
        assert AlertType.ERROR_DETECTED in alert_types
    
    def test_all_none_no_crash(self):
        """Test that all None values don't crash."""
        alerts = detect_alerts()
        # Should return some alerts for None absorption/float
        assert isinstance(alerts, list)


class TestAlertSummary:
    """Tests for alert summary generation."""
    
    def test_empty_alerts_summary(self):
        """Test summary with no alerts."""
        summary = get_alert_summary([])
        assert summary['total'] == 0
        assert summary['critical'] == 0
        assert summary['warning'] == 0
        assert summary['info'] == 0
    
    def test_mixed_alerts_summary(self):
        """Test summary with mixed alert types."""
        alerts = [
            AlertInfo(AlertType.CRITICAL_DISCHARGE, Severity.CRITICAL, "Test"),
            AlertInfo(AlertType.DEEP_DISCHARGE, Severity.WARNING, "Test"),
            AlertInfo(AlertType.NO_FLOAT, Severity.INFO, "Test"),
            AlertInfo(AlertType.NO_ABSORPTION, Severity.WARNING, "Test"),
        ]
        
        summary = get_alert_summary(alerts)
        
        assert summary['total'] == 4
        assert summary['critical'] == 1
        assert summary['warning'] == 2
        assert summary['info'] == 1
        assert summary['by_type']['critical_discharge'] == 1
        assert summary['by_type']['deep_discharge'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
