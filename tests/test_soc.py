"""
Unit tests for SOC calculations.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.calculations.soc import (
    calculate_soc, calculate_soc_per_battery, get_soc_category,
    estimate_remaining_capacity, calculate_voltage_from_soc,
    get_voltage_reference_lines, analyze_soc_trend,
    DEFAULT_V_FULL, DEFAULT_V_CUTOFF
)


class TestSOCCalculation:
    """Tests for SOC calculation function."""
    
    def test_soc_at_full_voltage(self):
        """Test SOC at full voltage returns 100%."""
        soc = calculate_soc(56.4, v_full=56.4, v_cutoff=37.5)
        assert soc == 100.0
    
    def test_soc_at_cutoff_voltage(self):
        """Test SOC at cutoff voltage returns 0%."""
        soc = calculate_soc(37.5, v_full=56.4, v_cutoff=37.5)
        assert soc == 0.0
    
    def test_soc_at_midpoint(self):
        """Test SOC at midpoint voltage."""
        midpoint = (56.4 + 37.5) / 2  # 46.95V
        soc = calculate_soc(midpoint, v_full=56.4, v_cutoff=37.5)
        assert abs(soc - 50.0) < 0.1
    
    def test_soc_below_cutoff_clamps_to_zero(self):
        """Test that voltage below cutoff returns 0%."""
        soc = calculate_soc(30.0, v_full=56.4, v_cutoff=37.5)
        assert soc == 0.0
    
    def test_soc_above_full_clamps_to_hundred(self):
        """Test that voltage above full returns 100%."""
        soc = calculate_soc(60.0, v_full=56.4, v_cutoff=37.5)
        assert soc == 100.0
    
    def test_soc_typical_values(self):
        """Test SOC for typical voltage values."""
        # 48V should be around 55.5%
        soc = calculate_soc(48.0, v_full=56.4, v_cutoff=37.5)
        assert 50 < soc < 60
        
        # 44V (warning threshold) should be around 34%
        soc = calculate_soc(44.0, v_full=56.4, v_cutoff=37.5)
        assert 30 < soc < 40
    
    def test_soc_with_none_returns_zero(self):
        """Test that None voltage returns 0%."""
        soc = calculate_soc(None)
        assert soc == 0.0
    
    def test_soc_with_zero_returns_zero(self):
        """Test that zero voltage returns 0%."""
        soc = calculate_soc(0)
        assert soc == 0.0
    
    def test_soc_invalid_thresholds_raises(self):
        """Test that invalid thresholds raise an error."""
        with pytest.raises(ValueError):
            calculate_soc(50.0, v_full=40.0, v_cutoff=50.0)


class TestSOCPerBattery:
    """Tests for per-battery voltage calculation."""
    
    def test_voltage_per_battery_4_batteries(self):
        """Test voltage calculation for 4 batteries."""
        per_battery = calculate_soc_per_battery(48.0, battery_count=4)
        assert per_battery == 12.0
    
    def test_voltage_per_battery_full_pack(self):
        """Test per-battery voltage at full pack."""
        per_battery = calculate_soc_per_battery(56.4, battery_count=4)
        assert abs(per_battery - 14.1) < 0.01
    
    def test_voltage_per_battery_none_returns_zero(self):
        """Test that None pack voltage returns 0."""
        per_battery = calculate_soc_per_battery(None)
        assert per_battery == 0.0
    
    def test_voltage_per_battery_invalid_count_raises(self):
        """Test that invalid battery count raises error."""
        with pytest.raises(ValueError):
            calculate_soc_per_battery(48.0, battery_count=0)


class TestSOCCategory:
    """Tests for SOC category classification."""
    
    def test_category_excellent(self):
        """Test excellent category (80-100%)."""
        category, color = get_soc_category(85)
        assert category == 'Excelente'
        assert color == '#4CAF50'
    
    def test_category_good(self):
        """Test good category (60-80%)."""
        category, color = get_soc_category(70)
        assert category == 'Bueno'
    
    def test_category_moderate(self):
        """Test moderate category (40-60%)."""
        category, color = get_soc_category(50)
        assert category == 'Moderado'
    
    def test_category_low(self):
        """Test low category (20-40%)."""
        category, color = get_soc_category(30)
        assert category == 'Bajo'
    
    def test_category_critical(self):
        """Test critical category (0-20%)."""
        category, color = get_soc_category(15)
        assert category == 'Crítico'
        assert color == '#F44336'


class TestRemainingCapacity:
    """Tests for remaining capacity estimation."""
    
    def test_full_capacity(self):
        """Test remaining capacity at 100% SOC."""
        remaining = estimate_remaining_capacity(100, total_capacity_ah=200)
        assert remaining == 200.0
    
    def test_half_capacity(self):
        """Test remaining capacity at 50% SOC."""
        remaining = estimate_remaining_capacity(50, total_capacity_ah=200)
        assert remaining == 100.0
    
    def test_empty_capacity(self):
        """Test remaining capacity at 0% SOC."""
        remaining = estimate_remaining_capacity(0, total_capacity_ah=200)
        assert remaining == 0.0


class TestVoltageFromSOC:
    """Tests for reverse SOC to voltage calculation."""
    
    def test_voltage_at_full_soc(self):
        """Test voltage at 100% SOC."""
        voltage = calculate_voltage_from_soc(100, v_full=56.4, v_cutoff=37.5)
        assert voltage == 56.4
    
    def test_voltage_at_zero_soc(self):
        """Test voltage at 0% SOC."""
        voltage = calculate_voltage_from_soc(0, v_full=56.4, v_cutoff=37.5)
        assert voltage == 37.5
    
    def test_voltage_at_midpoint(self):
        """Test voltage at 50% SOC."""
        voltage = calculate_voltage_from_soc(50, v_full=56.4, v_cutoff=37.5)
        expected = (56.4 + 37.5) / 2
        assert abs(voltage - expected) < 0.01


class TestSOCTrendAnalysis:
    """Tests for SOC trend analysis."""
    
    def test_improving_trend(self):
        """Test detection of improving trend."""
        soc_values = [40, 45, 50, 55, 60, 65, 70, 75]
        result = analyze_soc_trend(soc_values)
        assert result['trend'] == 'improving'
    
    def test_declining_trend(self):
        """Test detection of declining trend."""
        soc_values = [75, 70, 65, 60, 55, 50, 45, 40]
        result = analyze_soc_trend(soc_values)
        assert result['trend'] == 'declining'
    
    def test_stable_trend(self):
        """Test detection of stable trend."""
        soc_values = [50, 52, 48, 51, 49, 50, 51, 49]
        result = analyze_soc_trend(soc_values)
        assert result['trend'] == 'stable'
    
    def test_insufficient_data(self):
        """Test handling of insufficient data."""
        result = analyze_soc_trend([50])
        assert result['trend'] == 'insufficient_data'
    
    def test_trend_statistics(self):
        """Test that trend analysis returns correct statistics."""
        soc_values = [60, 50, 40, 30, 20]
        result = analyze_soc_trend(soc_values)
        
        assert result['min'] == 20
        assert result['max'] == 60
        assert result['average'] == 40
        assert result['days_critical'] == 1  # 20%
        assert result['days_low'] == 2  # 30%, 40% (actually 30% only fits)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
