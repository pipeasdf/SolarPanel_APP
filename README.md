# ☀️ Solar Panel Monitoring App

Sistema de monitoreo para paneles solares Victron con análisis de CSV, cálculo de SOC y alertas automáticas.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![SQLite](https://img.shields.io/badge/SQLite-3-green.svg)

## 📋 Descripción

Aplicación web ligera desarrollada en Streamlit para usuarios de sistemas fotovoltaicos Victron. Permite:

- **Subir y validar CSV** generados por Victron VE.Direct / MPPT / inversor
- **Almacenar datos** en SQLite con SQLAlchemy
- **Visualizar dashboard** con gráficos interactivos (Plotly)
- **Calcular SOC** del banco de baterías 48V
- **Detectar alertas** de descarga profunda y problemas de carga
- **Exportar informes** en CSV/Excel

## 🚀 Inicio Rápido

### Requisitos

- Python 3.9 o superior
- pip

### Instalación

```bash
# Clonar o descargar el proyecto
cd SolarPanel_APP

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
streamlit run app.py
```

La aplicación estará disponible en `http://localhost:8501`

## 📁 Estructura del Proyecto

```
SolarPanel_APP/
├── app.py                    # Punto de entrada principal
├── requirements.txt          # Dependencias Python
├── README.md                 # Esta documentación
│
├── src/
│   ├── database/
│   │   ├── models.py         # Modelos SQLAlchemy
│   │   └── connection.py     # Conexión a BD
│   │
│   ├── csv_processor/
│   │   ├── parser.py         # Parser CSV
│   │   └── column_mapper.py  # Mapeo de columnas
│   │
│   ├── calculations/
│   │   ├── soc.py            # Cálculos SOC
│   │   ├── alerts.py         # Detección de alertas
│   │   └── aggregations.py   # KPIs y estadísticas
│   │
│   └── utils/
│       └── export.py         # Exportación CSV/XLSX
│
├── pages/
│   ├── 1_📊_Dashboard.py     # Dashboard principal
│   ├── 2_📤_Upload.py        # Subir CSV
│   ├── 3_📁_Histórico.py     # Explorar datos
│   └── 4_⚙️_Configuración.py # Ajustes
│
├── data/
│   ├── solar_data.db         # Base de datos SQLite
│   └── samples/              # CSV de ejemplo
│
└── tests/                    # Tests unitarios
```

## 📊 Características

### Dashboard

- **KPIs**: Producción total, promedio diario, SOC medio, días con descarga profunda
- **Gráficos interactivos**:
  - Producción diaria (Wh)
  - Voltajes min/max con líneas de referencia
  - Tiempos de carga (bulk/absorption/float)
  - Histograma de SOC
- **Tabla de datos** con coloración por SOC
- **Panel de alertas** con filtro por severidad

### Cálculo de SOC

Fórmula de interpolación lineal:

```
SOC% = clip((V_measured - V_cutoff) / (V_full - V_cutoff) * 100, 0, 100)
```

Valores por defecto (ajustables):
- **V_full_pack**: 56.4V (100% SOC)
- **V_cutoff**: 37.5V (0% SOC)
- **V_warning**: 44V (advertencia)
- **V_critical**: 42V (crítico)

### Alertas Automáticas

| Tipo | Condición | Severidad |
|------|-----------|-----------|
| Descarga profunda | V_min < 44V | ⚠️ Warning |
| Descarga crítica | V_min < 42V | 🔴 Critical |
| Sin absorción | absorption = 0 | ⚠️ Warning |
| Sin flotación | float = 0 | ℹ️ Info |
| Error detectado | error_text ≠ null | ⚠️ Warning |

## 📋 Formato CSV

El sistema acepta CSV con las siguientes columnas (nombres flexibles):

| Columna Estándar | Nombres Aceptados |
|------------------|-------------------|
| timestamp | Date, Timestamp, Fecha |
| yield_wh | Yield(Wh), Producción, Energy |
| min_voltage | Min. battery voltage(V), Vmin |
| max_voltage | Max. battery voltage(V), Vmax |
| bulk_m | Time in bulk(m), Bulk |
| absorption_m | Time in absorption(m), Absorción |
| float_m | Time in float(m), Flotación |

### CSV de Ejemplo

Disponibles en `data/samples/`:
- `sample_complete.csv` - Datos completos
- `sample_alt_names.csv` - Nombres alternativos
- `sample_partial.csv` - Solo columnas requeridas

## ⚙️ Configuración del Sistema

Configurado para:
- **Sistema**: 5 kW fotovoltaico
- **Banco**: 4× NARADA MPG12V200 en serie (48V, 200Ah)
- **Ubicación**: La Unión, Los Ríos, Chile
- **Zona horaria**: America/Santiago

Todos los umbrales son ajustables desde la página de Configuración.

## 🧪 Tests

Ejecutar tests unitarios:

```bash
# Todos los tests
python -m pytest tests/ -v

# Tests específicos
python -m pytest tests/test_soc.py -v
python -m pytest tests/test_parser.py -v
python -m pytest tests/test_alerts.py -v
```

## 📦 Base de Datos

SQLite almacenado en `data/solar_data.db`:

- **records**: Registros diarios de producción
- **settings**: Configuración y umbrales
- **alerts**: Alertas detectadas

## 🔧 Desarrollo

### Agregar nuevos tipos de alertas

1. Añadir tipo en `src/calculations/alerts.py`:
   ```python
   class AlertType(Enum):
       NEW_ALERT = 'new_alert'
   ```

2. Crear función de detección:
   ```python
   def detect_new_alert(value: float) -> List[AlertInfo]:
       # Lógica de detección
   ```

3. Añadir a `detect_alerts()`

### Modificar umbrales por defecto

Editar `DEFAULT_SETTINGS` en `src/database/models.py`

## 📝 Notas Técnicas

- **SOC**: La estimación usa interpolación lineal, que es una aproximación práctica. La relación real voltaje-SOC es no lineal y depende de temperatura, corriente, y edad de las baterías.
- **Zona horaria**: Los CSV se interpretan con America/Santiago. Ajustable en Configuración.
- **Desgaste**: Las estimaciones de desgaste son aproximadas y dependen del historial completo.

## 📜 Licencia

MIT License - Uso libre para proyectos personales y comerciales.

## 🤝 Contribuciones

¡Contribuciones bienvenidas! Por favor:
1. Fork el repositorio
2. Crea una rama para tu feature
3. Envía un Pull Request

---

Desarrollado para sistemas Victron | La Unión, Los Ríos, Chile 🇨🇱
