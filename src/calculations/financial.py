"""
Financial calculations for the Solar Panel App.
"""
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database import Record

def calculate_total_savings(total_production_kwh: float, settings: Dict[str, str]) -> float:
    """
    Calculate total savings based on total production and current cost per kWh.
    """
    cost_kwh = float(settings.get('cost_kwh', '235.45'))
    return total_production_kwh * cost_kwh

def calculate_total_historical_savings(session: Session, settings: Dict[str, str]) -> float:
    """
    Calculate total savings querying ALL records in the database.
    """
    total_yield_wh = session.query(func.sum(Record.yield_wh)).scalar() or 0
    total_yield_kwh = total_yield_wh / 1000.0
    
    return calculate_total_savings(total_yield_kwh, settings)

def calculate_monthly_savings(monthly_production_kwh: float, settings: Dict[str, str]) -> float:
    """
    Calculate the savings for a specific month based on production.
    
    The rationale is: 
    Savings = (Production_kWh * Cost_per_kWh) + Fixed_Costs_Avoided?
    
    Actually, usually solar reduces the variable part (kWh). 
    Fixed costs are usually paid anyway unless off-grid.
    However, the user asked to "Comparar la energía producida vs el costo que habría tenido".
    So we can treat the production as if we had to buy it from the grid.
    
    Formula:
    Savings = (Yield_kWh * Cost_kWh) + (Proportional Fixed Costs?)
    
    For simplicity and based on common residential tariffs:
    We assume the detailed calculation requested involves fixed costs.
    If the user implies they are OFF-GRID or avoiding the bill entirely, we sum all.
    Let's assume the savings is strictly the value of the energy produced + 
    a portion of fixed costs if we assume the alternative was paying a full bill.
    
    Actually, let's keep it simple and robust:
    Savings = (Yield_kWh * cost_kwh)
    
    BUT, the user listed "Transport", "Admin", etc.
    Let's implement a 'Theoretical Bill' calculator.
    """
    cost_kwh = float(settings.get('cost_kwh', '235.45'))
    
    # Variable cost only (what you definitely save by generating your own kWh)
    variable_savings = monthly_production_kwh * cost_kwh
    
    return variable_savings

def calculate_theoretical_bill(kwh_consumed: float, settings: Dict[str, str]) -> float:
    """
    Calculate what the bill WOULD be for a given consumption.
    Includes fixed costs.
    """
    cost_kwh = float(settings.get('cost_kwh', '235.45'))
    cost_admin = float(settings.get('cost_admin', '1195'))
    cost_transport = float(settings.get('cost_transport', '3500'))
    cost_meter = float(settings.get('cost_meter_rent', '438'))
    
    variable_cost = kwh_consumed * cost_kwh
    fixed_cost = cost_admin + cost_transport + cost_meter
    
    return variable_cost + fixed_cost

def calculate_roi_metrics(total_savings_clp: float, settings: Dict[str, str]) -> Dict[str, Any]:
    """
    Calculate ROI indicators.
    """
    investment = float(settings.get('initial_investment', '5000000'))
    usd_rate = float(settings.get('usd_clp_rate', '950'))
    
    percentage = (total_savings_clp / investment) * 100 if investment > 0 else 0
    remaining = investment - total_savings_clp
    is_recovered = total_savings_clp >= investment
    
    return {
        'total_savings_clp': total_savings_clp,
        'total_savings_usd': total_savings_clp / usd_rate if usd_rate > 0 else 0,
        'investment_clp': investment,
        'roi_percentage': percentage,
        'is_recovered': is_recovered,
        'remaining_clp': remaining if remaining > 0 else 0,
        'status_text': "¡Inversión Recuperada!" if is_recovered else "En progreso"
    }
