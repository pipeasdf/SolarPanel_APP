"""
Upload Page - CSV Import for Solar Monitoring

Allows users to upload Victron CSV files, preview data,
validate columns, and import to the database.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_session_context, get_setting, Record, Alert, init_db
from src.csv_processor import parse_csv, preview_csv, validate_dataframe, COLUMN_MAPPINGS
from src.calculations.alerts import detect_alerts
from src.calculations.soc import calculate_soc


st.set_page_config(page_title="Upload - Solar Monitor", page_icon="📤", layout="wide")

st.title("📤 Subir Datos CSV")
st.markdown("---")

# Instructions
st.markdown("""
### 📋 Instrucciones

1. Exporta los datos desde tu aplicación Victron (VE.Direct, VictronConnect)
2. Sube el archivo CSV usando el botón de abajo
3. Revisa la validación de columnas
4. Confirma la importación

**Formatos soportados:** CSV con separador coma (,) o punto y coma (;)
""")

st.markdown("---")


# File uploader
uploaded_file = st.file_uploader(
    "Arrastra o selecciona un archivo CSV",
    type=['csv'],
    help="Archivos CSV exportados desde Victron VE.Direct o VictronConnect"
)


if uploaded_file is not None:
    # Read file content
    file_content = uploaded_file.read()
    
    st.success(f"✅ Archivo cargado: **{uploaded_file.name}** ({len(file_content)} bytes)")
    
    # Preview section
    st.markdown("---")
    st.subheader("👁️ Vista Previa")
    
    # Get preview
    preview_df, report = preview_csv(file_content, max_rows=50)
    
    # Show original columns
    st.markdown("**Columnas encontradas:**")
    st.code(", ".join(preview_df.columns.tolist()))
    
    # Show preview table
    st.dataframe(preview_df.head(50))
    
    # Validation section
    st.markdown("---")
    st.subheader("🔍 Validación de Columnas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**✅ Columnas mapeadas:**")
        for csv_col, std_col in report['mapping'].items():
            st.markdown(f"- `{csv_col}` → `{std_col}`")
        
        if report['unmapped_columns']:
            st.markdown("**⚪ Columnas no mapeadas (se ignorarán):**")
            for col in report['unmapped_columns']:
                st.markdown(f"- `{col}`")
    
    with col2:
        # Validation status
        if report['is_valid']:
            st.success("✅ **Validación exitosa**")
            st.markdown(f"- Columnas mapeadas: {report['mapped_columns']}/{report['total_columns']}")
            st.markdown(f"- Columnas requeridas: {report['required_found']}/{report['required_total']}")
        else:
            st.error("❌ **Validación fallida**")
            st.markdown("**Columnas requeridas faltantes:**")
            for col in report['missing_required']:
                st.markdown(f"- ❌ `{col}`")
        
        if report['missing_optional']:
            st.warning("**Columnas opcionales faltantes:**")
            for col in report['missing_optional']:
                st.markdown(f"- ⚠️ `{col}`")
    
    # Import section (only if valid)
    if report['is_valid']:
        st.markdown("---")
        st.subheader("📥 Importar Datos")
        
        # Parse full file
        df_parsed, parse_report = parse_csv(file_content)
        
        # Additional validation
        validation = validate_dataframe(df_parsed)
        
        # Show validation results
        if validation['warnings']:
            st.warning("⚠️ **Advertencias:**")
            for warning in validation['warnings']:
                st.markdown(f"- {warning}")
        
        st.info(f"""
        **Resumen de importación:**
        - Total de filas: {validation['row_count']}
        - Filas válidas: {validation['valid_rows']}
        - Período: {df_parsed['timestamp'].min()} a {df_parsed['timestamp'].max()}
        """)
        
        # Settings for import
        with st.expander("⚙️ Opciones de importación"):
            timezone = st.selectbox(
                "Zona horaria",
                options=['America/Santiago', 'UTC', 'America/Buenos_Aires'],
                index=0
            )
            
            st.info("""
            **Manejo inteligente de duplicados:**
            - Si la fecha ya existe, se comparan los tiempos de carga (bulk + absorption + float)
            - Si el nuevo registro tiene más minutos, se actualiza el existente
            - Si el existente tiene igual o más datos, se mantiene sin cambios
            """)
        
        # Import button
        if st.button("📥 Confirmar Importación", type="primary", use_container_width=True):
            # Get thresholds for alert detection
            v_full = float(get_setting('v_full_pack', '56.4'))
            v_cutoff = float(get_setting('v_cutoff', '37.5'))
            v_warning = float(get_setting('v_warning', '44.0'))
            v_critical = float(get_setting('v_critical', '42.0'))
            
            thresholds = {
                'v_warning': v_warning,
                'v_critical': v_critical
            }
            
            # Import to database
            imported = 0
            skipped = 0
            updated = 0
            errors = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with get_session_context() as session:
                total_rows = len(df_parsed)
                
                for idx, row in df_parsed.iterrows():
                    try:
                        # Check for existing record with same date
                        if pd.notna(row['timestamp']):
                            existing = session.query(Record).filter(
                                Record.timestamp == row['timestamp']
                            ).first()
                            
                            if existing:
                                # Calculate total charging time for comparison
                                new_bulk = int(row.get('bulk_m', 0)) if pd.notna(row.get('bulk_m')) else 0
                                new_absorption = int(row.get('absorption_m', 0)) if pd.notna(row.get('absorption_m')) else 0
                                new_float = int(row.get('float_m', 0)) if pd.notna(row.get('float_m')) else 0
                                new_total = new_bulk + new_absorption + new_float
                                
                                existing_total = existing.bulk_m + existing.absorption_m + existing.float_m
                                
                                # Compare: if all values are equal OR new has more minutes, update
                                if new_total > existing_total:
                                    # Update existing record with more complete data
                                    existing.yield_wh = float(row['yield_wh']) if pd.notna(row['yield_wh']) else existing.yield_wh
                                    existing.min_voltage = float(row['min_voltage']) if pd.notna(row['min_voltage']) else existing.min_voltage
                                    existing.max_voltage = float(row['max_voltage']) if pd.notna(row['max_voltage']) else existing.max_voltage
                                    existing.bulk_m = new_bulk
                                    existing.absorption_m = new_absorption
                                    existing.float_m = new_float
                                    existing.pv_power_max = float(row.get('pv_power_max')) if pd.notna(row.get('pv_power_max')) else existing.pv_power_max
                                    existing.pv_voltage_max = float(row.get('pv_voltage_max')) if pd.notna(row.get('pv_voltage_max')) else existing.pv_voltage_max
                                    existing.error_text = str(row.get('error_text', '')) if pd.notna(row.get('error_text')) else existing.error_text
                                    updated += 1
                                else:
                                    # Existing record is equal or more complete, skip
                                    skipped += 1
                                continue
                        
                        # Create record
                        record = Record(
                            timestamp=row['timestamp'],
                            yield_wh=float(row['yield_wh']) if pd.notna(row['yield_wh']) else 0,
                            min_voltage=float(row['min_voltage']) if pd.notna(row['min_voltage']) else 0,
                            max_voltage=float(row['max_voltage']) if pd.notna(row['max_voltage']) else 0,
                            bulk_m=int(row.get('bulk_m', 0)) if pd.notna(row.get('bulk_m')) else 0,
                            absorption_m=int(row.get('absorption_m', 0)) if pd.notna(row.get('absorption_m')) else 0,
                            float_m=int(row.get('float_m', 0)) if pd.notna(row.get('float_m')) else 0,
                            pv_power_max=float(row.get('pv_power_max')) if pd.notna(row.get('pv_power_max')) else None,
                            pv_voltage_max=float(row.get('pv_voltage_max')) if pd.notna(row.get('pv_voltage_max')) else None,
                            error_text=str(row.get('error_text', '')) if pd.notna(row.get('error_text')) else None,
                            created_at=datetime.utcnow()
                        )
                        session.add(record)
                        session.flush()  # Get the ID
                        
                        # Detect and store alerts
                        alerts = detect_alerts(
                            min_voltage=record.min_voltage,
                            max_voltage=record.max_voltage,
                            absorption_m=record.absorption_m,
                            float_m=record.float_m,
                            error_text=record.error_text,
                            thresholds=thresholds
                        )
                        
                        for alert_info in alerts:
                            alert = Alert(
                                record_id=record.id,
                                alert_type=alert_info.alert_type.value,
                                severity=alert_info.severity.value,
                                message=alert_info.message,
                                created_at=datetime.utcnow()
                            )
                            session.add(alert)
                        
                        imported += 1
                        
                    except Exception as e:
                        errors += 1
                        st.warning(f"Error en fila {idx}: {str(e)}")
                    
                    # Update progress
                    progress = (idx + 1) / total_rows
                    progress_bar.progress(progress)
                    status_text.text(f"Procesando... {idx + 1}/{total_rows}")
            
            progress_bar.empty()
            status_text.empty()
            
            # Results
            st.markdown("---")
            st.subheader("📊 Resultado de Importación")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Nuevos", imported)
            with col2:
                st.metric("Actualizados", updated, help="Registros con datos más completos")
            with col3:
                st.metric("Sin cambios", skipped, help="Registros existentes con datos iguales o más completos")
            with col4:
                st.metric("Errores", errors)
            
            if imported > 0 or updated > 0:
                st.success(f"✅ {imported} nuevos registros importados, {updated} actualizados.")
                st.balloons()
            
            if errors > 0:
                st.error(f"❌ Se encontraron {errors} errores durante la importación.")
    
    else:
        st.error("""
        ❌ No se puede importar el archivo debido a columnas faltantes.
        
        Por favor, verifica que tu CSV contenga las columnas requeridas
        o utiliza nombres de columna compatibles.
        """)
        
        # Show expected column names
        st.markdown("---")
        st.subheader("📖 Nombres de Columna Aceptados")
        
        for std_col, alternatives in COLUMN_MAPPINGS.items():
            with st.expander(f"**{std_col}** {'(requerida)' if std_col in ['timestamp', 'yield_wh', 'min_voltage', 'max_voltage'] else '(opcional)'}"):
                st.markdown("Nombres aceptados:")
                for alt in alternatives:
                    st.markdown(f"- `{alt}`")

else:
    # No file uploaded - show sample format
    st.markdown("---")
    st.subheader("📋 Formato CSV Esperado")
    
    st.markdown("""
    El archivo CSV debe contener las siguientes columnas (los nombres pueden variar):
    """)
    
    sample_data = {
        'Date': ['2024-01-15', '2024-01-16', '2024-01-17'],
        'Yield(Wh)': [4500, 5200, 3800],
        'Min. battery voltage(V)': [47.2, 48.1, 45.5],
        'Max. battery voltage(V)': [55.8, 56.2, 55.1],
        'Time in bulk(m)': [180, 165, 210],
        'Time in absorption(m)': [60, 75, 45],
        'Time in float(m)': [120, 135, 90]
    }
    
    sample_df = pd.DataFrame(sample_data)
    st.dataframe(sample_df)
    
    # Download sample CSV
    csv_sample = sample_df.to_csv(index=False)
    st.download_button(
        label="📥 Descargar CSV de ejemplo",
        data=csv_sample,
        file_name="sample_victron_data.csv",
        mime="text/csv"
    )
