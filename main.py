import os
import json
import csv
import google.generativeai as genai
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
import argparse
import logging
import atexit
import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Cargar variables de entorno
load_dotenv()

# Configurar Gemini con manejo de errores
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    logging.error(f"Error configurando Gemini: {e}")
    raise

class SAPTableAgent:
    def __init__(self):
        try:
            self.model = genai.GenerativeModel('gemini-pro')
            self.base_url = "https://leanx.eu/en/sap/table/{}.html"
            logging.info("Modelo Gemini inicializado correctamente")
        except Exception as e:
            logging.error(f"Error inicializando el modelo: {e}")
            raise
    
    def extract_table_info(self, html_content):
        """Extrae la información de la tabla del HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        table_name = soup.find('h1').text.split()[-1] if soup.find('h1') else ""
        table_description = soup.find('h2').text if soup.find('h2') else ""
        
        fields = []
        table = soup.find('table', {'class': 'table-condensed'})
        if table:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) >= 8:
                    field = {
                        "name": cols[0].text.strip(),
                        "description": cols[1].text.strip(),
                        "data_element": cols[2].text.strip(),
                        "type": cols[4].text.strip(),
                        "length": cols[6].text.strip(),
                        "decimals": cols[7].text.strip()
                    }
                    fields.append(field)
        
        return {
            "name": table_name,
            "description": table_description,
            "fields": fields
        }
    
    def save_json(self, data, output_path):
        """Guarda los datos en un archivo JSON"""
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Guardar el archivo JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"\nArchivo JSON guardado exitosamente en: {output_path}")
            return True
        except Exception as e:
            print(f"Error guardando el archivo JSON: {str(e)}")
            return False
    
    def process_url(self, url):
        """Procesa la URL y genera el JSON con la estructura de la tabla"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            table_info = self.extract_table_info(response.text)
            
            prompt = f"""
            Analiza esta estructura de tabla SAP y proporciona una descripción detallada:
            Tabla: {table_info['name']}
            Descripción actual: {table_info['description']}
            Campos: {json.dumps(table_info['fields'], indent=2)}
            
            Genera una descripción técnica que incluya:
            1. Propósito principal de la tabla
            2. Relaciones clave con otras tablas
            3. Casos de uso comunes
            """
            
            response = self.model.generate_content(prompt)
            
            # Agregar agent_feedback dentro de table_info
            table_info["agent_feedback"] = {
                "analysis": response.text.strip() if response.text else "",
                "timestamp": datetime.datetime.now().isoformat(),
                "model": "gemini-pro",
                "prompt_version": "1.0"
            }
            
            output_path = os.getenv("OUTPUT_PATH", "output/output.json")
            self.save_json(table_info, output_path)
            
            return table_info
            
        except Exception as e:
            logging.error(f"Error procesando la URL: {str(e)}")
            return {"error": str(e)}
    
    def process_tables_from_csv(self, csv_path):
        """Procesa múltiples tablas desde un archivo CSV"""
        try:
            results = []
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    table_name = row['table_name']
                    logging.info(f"Procesando tabla: {table_name}")
                    
                    url = self.base_url.format(table_name.lower())
                    result = self.process_url(url)
                    results.append(result)
                    
                    # Guardar resultado individual
                    output_path = os.path.join('output', f'{table_name.lower()}.json')
                    self.save_json(result, output_path)
            
            # Guardar resultado consolidado
            consolidated = {
                "processed_at": datetime.datetime.now().isoformat(),
                "tables": results
            }
            self.save_json(consolidated, 'output/consolidated.json')
            return results
            
        except Exception as e:
            logging.error(f"Error procesando CSV: {str(e)}")
            return {"error": str(e)}

def cleanup():
    """Función de limpieza para ejecutar antes de cerrar"""
    try:
        logging.info("Limpiando recursos...")
        # Aquí podemos agregar cualquier limpieza necesaria
    except Exception as e:
        logging.error(f"Error durante la limpieza: {e}")

def main():
    # Registrar función de limpieza
    atexit.register(cleanup)
    
    try:
        parser = argparse.ArgumentParser(description='Extractor de estructuras de tablas SAP')
        parser.add_argument('--csv', default='input/sap_tables.csv',
                          help='Ruta al archivo CSV con las tablas SAP')
        parser.add_argument('--url', help='URL específica de una tabla SAP (opcional)')
        args = parser.parse_args()
        
        agent = SAPTableAgent()
        
        if args.url:
            # Procesar una sola URL si se proporciona
            logging.info(f"Procesando URL: {args.url}")
            result = agent.process_url(args.url)
        else:
            # Procesar tablas desde CSV
            logging.info(f"Procesando tablas desde CSV: {args.csv}")
            result = agent.process_tables_from_csv(args.csv)
        
        if "error" not in result:
            logging.info("Proceso completado exitosamente")
        else:
            logging.error(f"Error en el proceso: {result['error']}")
            
        print("\nEstructura(s) de tabla(s) SAP extraída(s):")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        logging.error(f"Error en la ejecución: {e}")
        raise
    finally:
        logging.info("Finalizando proceso")

if __name__ == "__main__":
    main()