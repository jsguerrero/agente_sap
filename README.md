# Agente Extractor de Estructuras SAP

## Resumen Ejecutivo

### Objetivo
Automatizar la extracción y documentación de estructuras de tablas SAP, enriqueciendo la información técnica mediante IA generativa para facilitar el entendimiento y mantenimiento de sistemas SAP.

### Fases de Funcionamiento
1. **Extracción**: Obtención de estructuras de tablas desde leanx.eu
2. **Procesamiento**: Análisis y estructuración de la información técnica
3. **Enriquecimiento**: Generación de documentación detallada mediante Gemini
4. **Consolidación**: Creación de archivos JSON individuales y consolidados

### Configuraciones Necesarias
1. **API Key de Google**: Requerida para acceder a Gemini
   - Crear cuenta en Google Cloud
   - Habilitar API de Gemini
   - Generar y configurar API key en .env

2. **Docker (Recomendado)**:
   - Docker Desktop instalado
   - Docker Compose disponible

3. **Entrada de Datos**:
   - CSV con listado de tablas a procesar
   - Acceso a internet para consultar leanx.eu

## Documentación Técnica

### Preparación del Entorno

1. **Estructura de Directorios**:   ```bash
   # Crear directorio de salida
   mkdir -p output

2. **Variables de Entorno**:   ```bash
   # Crear archivo .env
   echo "GOOGLE_API_KEY=tu_api_key" > .env   ```

### Instalación y Uso

#### Con Docker (Recomendado)
1. Construir imagen:   ```bash
   docker-compose build   ```

2. Ejecutar contenedor:   ```bash
   docker-compose up   ```

#### Manualmente
1. Instalar dependencias:   ```bash
   pip install -r requirements.txt   ```

2. Ejecutar script:   ```bash
   # Para una tabla específica
   python main.py --url https://leanx.eu/en/sap/table/marc.html

   # Para procesar múltiples tablas
   python main.py --csv input/sap_tables.csv   ```

### Estructura del Proyecto

/agente_sap
├── input/                    # Entrada de datos
│   └── sap_tables.csv       # Configuración de tablas
├── output/                  # Resultados
│   ├── consolidated.json   # Datos consolidados
│   └── {table}.json       # Resultados individuales
├── main.py                 # Script principal
├── Dockerfile             # Configuración Docker
└── docker-compose.yml    # Orquestación de contenedores

### Formato de Datos

#### CSV de Entrada
table_name,description
MARC,Plant Data for Material
MARA,General Material Data

#### JSON de Salida
{
  "name": "MARC",
  "description": "Plant Data for Material",
  "fields": [
    {
      "name": "FIELD_NAME",
      "description": "Field Description",
      "data_element": "DATA_ELEMENT",
      "type": "TYPE",
      "length": "LENGTH",
      "decimals": "DECIMALS"
    }
  ],
  "agent_feedback": {
    "analysis": "Análisis detallado",
    "timestamp": "2024-03-14T15:30:45",
    "model": "gemini-pro",
    "prompt_version": "1.0"
  }
}

### Dependencias
- google.generativeai: Integración con Gemini
- beautifulsoup4: Procesamiento HTML
- requests: Peticiones HTTP
- python-dotenv: Gestión de configuración

### Consideraciones Técnicas
- Manejo de errores y reintentos en peticiones HTTP
- Limpieza y validación de datos extraídos
- Gestión de memoria en procesamiento por lotes
- Logging para diagnóstico y monitoreo
- Control de versiones en análisis de IA

### Limitaciones y Consideraciones
- Dependencia de disponibilidad de leanx.eu
- Cuotas y límites de API de Gemini
- Variabilidad en calidad de análisis de IA
- Necesidad de validación manual de resultados críticos
  