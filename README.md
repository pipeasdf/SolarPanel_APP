# ☀️ Victron Solar History & Monitoring App
> **Preserving and analyzing your off-grid energy data beyond the 30-day limit.**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-3-green.svg)](https://www.sqlite.org/)

## 📋 The Problem & Solution

As an **Off-Grid** solar user with a **Victron VE.Direct Bluetooth Dongle**, the official VictronConnect app only stores **30 days of historical data**. This makes it impossible to perform long-term seasonal analysis or track the system's performance over the years.

This application was developed to:
1. **Bypass the 30-day limit**: By importing CSV reports from the Victron app, this local tool stores your entire history in a permanent SQLite database.
2. **Dynamic Financial Analysis**: Even though the system is Off-Grid, this tool calculates "Theoretical Savings" by comparing solar production against real electricity company rates.
3. **Advanced Battery Health**: Provides automated SOC (State of Charge) estimation and deep discharge alerts for 48V battery banks.

## 🚀 Key Features

- **📤 Data Persistence**: Upload CSV files exported from VictronConnect and build a lifetime history.
- **📊 Interactive Dashboard**: High-level KPIs and detailed charts (Plotly) for yield (Wh), battery voltages, and charge stages (Bulk/Absorption/Float).
- **💰 Financial Module**: Custom configuration of energy costs (kWh price, fixed charges, meter rental) to track ROI (Return on Investment).
- **🔋 Battery Monitoring**: Linear SOC interpolation for 48V banks and automated detection of critical voltage events.
- **💡 Smart Interpretation**: Built-in logic to interpret daily data and provide health summaries.

## 📁 Project Structure

```
SolarPanel_APP/
├── app.py                    # Main application entry point
├── requirements.txt          # Python dependencies
├── src/
│   ├── database/             # SQLite/SQLAlchemy models and connection
│   ├── csv_processor/        # Flexible CSV parsing logic
│   ├── calculations/         # SOC, Financial, and KPI logic
│   └── utils/                # Export and formatting utilities
├── pages/                    # Multi-page Streamlit interface
└── data/                     # Local SQLite database (gitignored)
```

## ⚙️ Quick Start

### Prerequisites
- Python 3.12+ (Tested on 3.14)
- pip

### Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USER/SolarPanel_APP.git
   cd SolarPanel_APP
   ```

2. **Setup Virtual Environment:**
   ```bash
   python -m venv .venv
   # Windows
   .\.venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the App:**
   ```bash
   streamlit run app.py
   ```

## 🔋 SOC Estimation Note
The system uses professional interpolation for 48V banks (Default: 4x 12V batteries). 
- **100% SOC**: 56.4V
- **0% SOC**: 37.5V
*These thresholds are fully adjustable within the app's configuration panel.*

## 📜 License
MIT License - Created for the Victron Community in Chile 🇨🇱.

