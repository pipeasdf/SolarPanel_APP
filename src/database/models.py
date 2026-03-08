"""
SQLAlchemy models for the Solar Panel Monitoring App.

Tables:
- Record: Daily solar production records from Victron CSV
- Setting: App configuration and thresholds
- Alert: Cached detected alerts per date
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Text, ForeignKey, 
    create_engine, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Record(Base):
    """
    Daily solar production record from Victron CSV.
    
    Stores energy production, voltage readings, and charge time data
    for analysis and SOC calculations.
    """
    __tablename__ = 'records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    yield_wh = Column(Float, nullable=False)  # Energy produced (Wh)
    
    # Voltage readings (48V pack)
    min_voltage = Column(Float, nullable=False)  # Minimum battery voltage
    max_voltage = Column(Float, nullable=False)  # Maximum battery voltage
    
    # Charge time in minutes
    bulk_m = Column(Integer, default=0)        # Time in bulk charging
    absorption_m = Column(Integer, default=0)  # Time in absorption
    float_m = Column(Integer, default=0)       # Time in float
    
    # Optional PV data
    pv_power_max = Column(Float, nullable=True)    # Max PV power (W)
    pv_voltage_max = Column(Float, nullable=True)  # Max PV voltage (V)
    
    # Error information
    error_text = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    alerts = relationship("Alert", back_populates="record", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_records_timestamp_date', timestamp),
        Index('idx_records_min_voltage', min_voltage),
    )
    
    def __repr__(self):
        return f"<Record(id={self.id}, timestamp={self.timestamp}, yield={self.yield_wh}Wh)>"
    
    @property
    def date(self):
        """Return just the date portion of timestamp."""
        return self.timestamp.date() if self.timestamp else None


class Setting(Base):
    """
    App configuration and threshold settings.
    
    Stores key-value pairs for app configuration, organized by category.
    Categories: 'thresholds', 'system', 'ui', 'general'
    """
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    category = Column(String(50), default='general')
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Setting(key={self.key}, value={self.value})>"


class Alert(Base):
    """
    Cached detected alerts per date.
    
    Alert types:
    - deep_discharge: min_voltage < 44V
    - critical_discharge: min_voltage < 42V
    - near_cutoff: min_voltage < 40V
    - no_absorption: absorption_m == 0
    - no_float: float_m == 0
    - error_detected: error_text is not null
    
    Severity levels: 'info', 'warning', 'critical'
    """
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey('records.id', ondelete='CASCADE'), nullable=False)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)  # 'info', 'warning', 'critical'
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    record = relationship("Record", back_populates="alerts")
    
    # Indexes
    __table_args__ = (
        Index('idx_alerts_record_id', record_id),
        Index('idx_alerts_severity', severity),
        Index('idx_alerts_type', alert_type),
    )
    
    def __repr__(self):
        return f"<Alert(id={self.id}, type={self.alert_type}, severity={self.severity})>"


# Default settings to initialize
DEFAULT_SETTINGS = [
    # Threshold settings
    {
        'key': 'v_full_pack',
        'value': '56.4',
        'category': 'thresholds',
        'description': 'Full pack voltage at 100% SOC (4 × 14.1V float)'
    },
    {
        'key': 'v_cutoff',
        'value': '37.5',
        'category': 'thresholds',
        'description': 'Cutoff voltage at 0% SOC'
    },
    {
        'key': 'v_warning',
        'value': '44.0',
        'category': 'thresholds',
        'description': 'Warning threshold for deep discharge'
    },
    {
        'key': 'v_critical',
        'value': '42.0',
        'category': 'thresholds',
        'description': 'Critical threshold for discharge'
    },
    # System settings
    {
        'key': 'system_power_kw',
        'value': '5.0',
        'category': 'system',
        'description': 'Installed system power in kW'
    },
    {
        'key': 'battery_count',
        'value': '4',
        'category': 'system',
        'description': 'Number of batteries in series'
    },
    {
        'key': 'battery_voltage',
        'value': '12',
        'category': 'system',
        'description': 'Individual battery voltage (V)'
    },
    {
        'key': 'battery_capacity_ah',
        'value': '200',
        'category': 'system',
        'description': 'Battery capacity in Ah'
    },
    {
        'key': 'battery_model',
        'value': 'NARADA MPG12V200',
        'category': 'system',
        'description': 'Battery model name'
    },
    # UI settings
    {
        'key': 'timezone',
        'value': 'America/Santiago',
        'category': 'ui',
        'description': 'Timezone for date parsing'
    },
    {
        'key': 'color_success',
        'value': '#4CAF50',
        'category': 'ui',
        'description': 'Success/good color (green)'
    },
    {
        'key': 'color_info',
        'value': '#2196F3',
        'category': 'ui',
        'description': 'Info color (blue)'
    },
    {
        'key': 'color_warning',
        'value': '#FFC107',
        'category': 'ui',
        'description': 'Warning color (amber)'
    },
    {
        'key': 'color_danger',
        'value': '#F44336',
        'category': 'ui',
        'description': 'Danger/critical color (red)'
    },
    {
        'key': 'color_background',
        'value': '#F5F5F5',
        'category': 'ui',
        'description': 'Background color (light gray)'
    },
    # Financial settings
    {
        'key': 'initial_investment',
        'value': '5000000',
        'category': 'financial',
        'description': 'Initial investment in CLP'
    },
    {
        'key': 'cost_admin',
        'value': '1195',
        'category': 'financial',
        'description': 'Monthly administration fixed cost (CLP)'
    },
    {
        'key': 'cost_transport',
        'value': '3500',
        'category': 'financial',
        'description': 'Monthly transport fixed cost (CLP)'
    },
    {
        'key': 'cost_kwh',
        'value': '235.45',
        'category': 'financial',
        'description': 'Cost per kWh (CLP)'
    },
    {
        'key': 'cost_meter_rent',
        'value': '438',
        'category': 'financial',
        'description': 'Monthly meter rental cost (CLP)'
    },
    {
        'key': 'usd_clp_rate',
        'value': '950',
        'category': 'financial',
        'description': 'Exchange rate CLP to USD'
    },
]
