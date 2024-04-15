import streamlit as st
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
import io
import openpyxl

# URL de la hoja de Google Sheets (formato CSV)
data_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQdDDfArcx0T6u4niPfQgnp1R0gwIKn9NMCRsSS9B12BzNh6Gw4TBPwYmYxqRKldRvtVJJEF4W-JZJs/pub?gid=0&single=true&output=csv"

# Función para cargar los datos desde la URL
def load_data_from_url(url):
    try:
        data = pd.read_csv(url)
        st.success("Datos cargados correctamente")
        return data
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return None

def calculate_kpis(data):
    date_columns = ['Fecha CartaConsulta', 'FechaAprobacion', 'FechaVigencia', 'FechaElegibilidad', 'FechadePrimerDesembolso']
    for col in date_columns:
        data[col] = pd.to_datetime(data[col], format='%d/%m/%Y', errors='coerce')

    def get_approx_months_diff(later_date, earlier_date):
        if pd.notna(later_date) and pd.notna(earlier_date):
            # Calcula la diferencia en días y convierte a meses aproximados
            days_diff = (later_date - earlier_date).days
            return round(days_diff / 30)  # Redondea al número entero más cercano
        return None

    # Calcula las diferencias y extrae los años
    data['KPI Aprobacion'] = data.apply(lambda x: get_approx_months_diff(x['FechaAprobacion'], x['Fecha CartaConsulta']), axis=1)
    data['KPI Vigencia'] = data.apply(lambda x: get_approx_months_diff(x['FechaVigencia'], x['FechaAprobacion']), axis=1)
    data['KPI Elegibilidad'] = data.apply(lambda x: get_approx_months_diff(x['FechaElegibilidad'], x['FechaVigencia']), axis=1)
    data['KPI Primer Desembolso'] = data.apply(lambda x: get_approx_months_diff(x['FechadePrimerDesembolso'], x['FechaElegibilidad']), axis=1)

    return data

def transform_data(data):
    # Asegurar que los datos están limpios y no hay duplicados o problemas de orden
    data = data.drop_duplicates()

    # Convertir las columnas de fechas a formato datetime y calcular los KPIs
    date_columns = ['Fecha CartaConsulta', 'FechaAprobacion', 'FechaVigencia', 'FechaElegibilidad', 'FechadePrimerDesembolso']
    for col in date_columns:
        data[col] = pd.to_datetime(data[col], errors='coerce')

    data['KPI Aprobacion'] = data.apply(lambda x: relativedelta(x['FechaAprobacion'], x['Fecha CartaConsulta']).months if pd.notna(x['FechaAprobacion']) and pd.notna(x['Fecha CartaConsulta']) else None, axis=1)
    data['KPI Vigencia'] = data.apply(lambda x: relativedelta(x['FechaVigencia'], x['FechaAprobacion']).months if pd.notna(x['FechaVigencia']) and pd.notna(x['FechaAprobacion']) else None, axis=1)
    data['KPI Elegibilidad'] = data.apply(lambda x: relativedelta(x['FechaElegibilidad'], x['FechaVigencia']).months if pd.notna(x['FechaElegibilidad']) and pd.notna(x['FechaVigencia']) else None, axis=1)
    data['KPI Primer Desembolso'] = data.apply(lambda x: relativedelta(x['FechadePrimerDesembolso'], x['FechaElegibilidad']).months if pd.notna(x['FechadePrimerDesembolso']) and pd.notna(x['FechaElegibilidad']) else None, axis=1)

    # Usar pd.melt para transformar las columnas de KPI en filas
    melted_data = pd.melt(data, 
                          id_vars=['IDEtapa', 'NoEtapa', 'Pais', 'EstadoColumnaGOP', 'Alias', 'Sector', 'SubSector',
                                   'Fecha CartaConsulta', 'FechaAprobacion', 'FechaVigencia', 'FechaElegibilidad', 
                                   'FechadePrimerDesembolso'],
                          value_vars=['KPI Aprobacion', 'KPI Vigencia', 'KPI Elegibilidad', 'KPI Primer Desembolso'],
                          var_name='Estaciones', value_name='KPI')

    # Mapeo correcto de los años según las fechas correspondientes
    year_mapping = {
        'Aprobacion': 'FechaAprobacion',
        'Vigencia': 'FechaVigencia',
        'Elegibilidad': 'FechaElegibilidad',
        'Primer Desembolso': 'FechadePrimerDesembolso'
    }

    # Extraer el año correcto utilizando el mapeo y asegurando que los nombres estén bien formateados
    melted_data['Año'] = melted_data['Estaciones'].apply(lambda x: data[year_mapping[x.replace('KPI ', '')]].dt.year.iloc[0])

    # Filtrar valores nulos y negativos
    melted_data = melted_data[melted_data['KPI'].notna() & (melted_data['KPI'] >= 0)]

    return melted_data[['IDEtapa', 'Estaciones', 'KPI', 'Año','NoEtapa', 'Pais', 'EstadoColumnaGOP', 'Alias', 'Sector', 'SubSector']]







# Función para convertir DataFrame a Excel
def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

# Aplicación principal de Streamlit
def main():
    st.title('Procesamiento de Datos desde Google Sheets')
    
    data = load_data_from_url(data_url)
    if data is not None:
        data = calculate_kpis(data)
        data_long_format = transform_data(data)
        st.write(data_long_format)  # Mostrar los datos en formato largo en la aplicación
            
        # Botón de descarga para Excel
        if st.button('Descargar datos transformados como Excel'):
            excel_data = convert_df_to_excel(data_long_format)
            st.download_button(label="Descargar como Excel",
                               data=excel_data,
                               file_name='transformed_data.xlsx',
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == "__main__":
    main()



