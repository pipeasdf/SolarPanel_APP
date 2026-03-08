"""
Unit tests for CSV parsing and column mapping.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.csv_processor import parse_csv, preview_csv, validate_dataframe, map_columns
from src.csv_processor.column_mapper import find_standard_column, normalize_column_name


class TestColumnMapper:
    """Tests for column mapping functionality."""
    
    def test_normalize_column_name(self):
        """Test column name normalization."""
        assert normalize_column_name("  Date  ") == "date"
        assert normalize_column_name("Min. battery voltage(V)") == "min. battery voltage(v)"
        assert normalize_column_name("Yield  (Wh)") == "yield (wh)"
    
    def test_find_standard_column_date(self):
        """Test mapping of date columns."""
        assert find_standard_column("Date") == "timestamp"
        assert find_standard_column("Timestamp") == "timestamp"
        assert find_standard_column("Fecha") == "timestamp"
        assert find_standard_column("fecha") == "timestamp"
    
    def test_find_standard_column_yield(self):
        """Test mapping of yield columns."""
        assert find_standard_column("Yield(Wh)") == "yield_wh"
        assert find_standard_column("Yield (Wh)") == "yield_wh"
        assert find_standard_column("Producción") == "yield_wh"
    
    def test_find_standard_column_voltage(self):
        """Test mapping of voltage columns."""
        assert find_standard_column("Min. battery voltage(V)") == "min_voltage"
        assert find_standard_column("Min voltage") == "min_voltage"
        assert find_standard_column("Vmin") == "min_voltage"
        assert find_standard_column("Max. battery voltage(V)") == "max_voltage"
        assert find_standard_column("Vmax") == "max_voltage"
    
    def test_find_standard_column_charging(self):
        """Test mapping of charging time columns."""
        assert find_standard_column("Time in bulk(m)") == "bulk_m"
        assert find_standard_column("Time in absorption(m)") == "absorption_m"
        assert find_standard_column("Time in float(m)") == "float_m"
    
    def test_find_standard_column_unknown(self):
        """Test that unknown columns return None."""
        assert find_standard_column("Unknown Column") is None
        assert find_standard_column("Random Data") is None
    
    def test_map_columns_complete(self):
        """Test mapping with complete set of columns."""
        csv_columns = [
            "Date", "Yield(Wh)", "Min. battery voltage(V)", "Max. battery voltage(V)",
            "Time in bulk(m)", "Time in absorption(m)", "Time in float(m)"
        ]
        mapping, unmapped, missing = map_columns(csv_columns)
        
        assert len(mapping) == 7
        assert len(unmapped) == 0
        assert len(missing) == 0
    
    def test_map_columns_missing_required(self):
        """Test detection of missing required columns."""
        csv_columns = ["Date", "Yield(Wh)"]  # Missing voltage columns
        mapping, unmapped, missing = map_columns(csv_columns)
        
        assert "min_voltage" in missing
        assert "max_voltage" in missing


class TestCSVParser:
    """Tests for CSV parsing functionality."""
    
    @pytest.fixture
    def sample_csv_complete(self):
        """Sample complete CSV content."""
        return """Date,Yield(Wh),Min. battery voltage(V),Max. battery voltage(V),Time in bulk(m),Time in absorption(m),Time in float(m)
2024-01-15,4520,48.2,55.8,185,62,118
2024-01-16,5180,49.1,56.1,175,71,134
2024-01-17,3850,46.5,55.2,205,45,85"""
    
    @pytest.fixture
    def sample_csv_alt_names(self):
        """Sample CSV with alternative column names."""
        return """Fecha,Producción (Wh),Vmin,Vmax,Bulk,Absorción,Float
15/01/2024,4520,48.2,55.8,185,62,118
16/01/2024,5180,49.1,56.1,175,71,134"""
    
    @pytest.fixture
    def sample_csv_minimal(self):
        """Sample minimal CSV with only required columns."""
        return """Timestamp,Yield(Wh),Min voltage,Max voltage
2024-01-15,4520,48.2,55.8
2024-01-16,5180,49.1,56.1"""
    
    def test_parse_complete_csv(self, sample_csv_complete):
        """Test parsing a complete CSV."""
        df, report = parse_csv(sample_csv_complete)
        
        assert report['is_valid'] == True
        assert len(df) == 3
        assert 'timestamp' in df.columns
        assert 'yield_wh' in df.columns
        assert 'min_voltage' in df.columns
        assert 'max_voltage' in df.columns
    
    def test_parse_alt_names_csv(self, sample_csv_alt_names):
        """Test parsing CSV with alternative column names."""
        df, report = parse_csv(sample_csv_alt_names)
        
        assert report['is_valid'] == True
        assert len(df) == 2
        assert 'timestamp' in df.columns
        assert 'yield_wh' in df.columns
    
    def test_parse_minimal_csv(self, sample_csv_minimal):
        """Test parsing minimal CSV."""
        df, report = parse_csv(sample_csv_minimal)
        
        assert report['is_valid'] == True
        assert len(df) == 2
        # Should have default values for optional columns
        assert 'bulk_m' in df.columns
        assert 'absorption_m' in df.columns
        assert 'float_m' in df.columns
    
    def test_parse_invalid_csv(self):
        """Test parsing CSV with missing required columns."""
        invalid_csv = """Date,SomeColumn
2024-01-15,100
2024-01-16,200"""
        
        df, report = parse_csv(invalid_csv)
        
        assert report['is_valid'] == False
        assert len(report['missing_required']) > 0
    
    def test_preview_csv(self, sample_csv_complete):
        """Test CSV preview functionality."""
        df, report = preview_csv(sample_csv_complete, max_rows=2)
        
        assert len(df) == 2
        assert 'mapping' in report
        assert 'is_valid' in report


class TestDataFrameValidation:
    """Tests for DataFrame validation."""
    
    def test_validate_valid_dataframe(self):
        """Test validation of valid DataFrame."""
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2024-01-15', '2024-01-16']),
            'yield_wh': [4520, 5180],
            'min_voltage': [48.2, 49.1],
            'max_voltage': [55.8, 56.1]
        })
        
        result = validate_dataframe(df)
        
        assert result['is_valid'] == True
        assert result['valid_rows'] == 2
    
    def test_validate_with_null_timestamps(self):
        """Test validation with null timestamps."""
        df = pd.DataFrame({
            'timestamp': [pd.Timestamp('2024-01-15'), None],
            'yield_wh': [4520, 5180],
            'min_voltage': [48.2, 49.1],
            'max_voltage': [55.8, 56.1]
        })
        
        result = validate_dataframe(df)
        
        assert result['is_valid'] == True
        assert len(result['warnings']) > 0
    
    def test_validate_with_invalid_voltages(self):
        """Test validation with out-of-range voltages."""
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2024-01-15', '2024-01-16']),
            'yield_wh': [4520, 5180],
            'min_voltage': [48.2, 150.0],  # Invalid voltage
            'max_voltage': [55.8, 56.1]
        })
        
        result = validate_dataframe(df)
        
        assert result['is_valid'] == True  # Still valid, just with warnings
        assert len(result['warnings']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
