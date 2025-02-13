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
        
        # Agregar extracción de foreign keys
        foreign_keys = []
        fk_table = soup.find_all('table')[1] if len(soup.find_all('table')) > 1 else None
        if fk_table:
            for row in fk_table.find_all('tr')[1:]:  # Skip header row
                cols = row.find_all('td')
                if len(cols) >= 6:
                    fk = {
                        "table": cols[0].text.strip(),
                        "field": cols[1].text.strip(),
                        "foreign_key_table": cols[2].text.strip(),
                        "foreign_key_field": cols[3].text.strip(),
                        "check_table": cols[4].text.strip(),
                        "check_field": cols[5].text.strip()
                    }
                    foreign_keys.append(fk)
        
        return {
            "name": table_name,
            "description": table_description,
            "fields": fields,
            "foreign_keys": foreign_keys
        }
    
    def save_json(self, data, output_path):
        """Guarda los datos en un archivo JSON"""
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Guardar el archivo JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logging.error(f"Error guardando el archivo JSON: {str(e)}")
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
            Relaciones de clave foránea: {json.dumps(table_info['foreign_keys'], indent=2)}
            
            Genera una descripción técnica que incluya:
            1. Propósito principal de la tabla
            2. Relaciones clave con otras tablas (basado en las foreign keys proporcionadas)
            3. Casos de uso comunes
            3. Sea clara y concisa
            4. Sea breve (máximo 2 líneas)
            5. Use terminología profesional
            6. Responde en ingles
            5. No incluya ejemplos específicos en la descripción
            """
            
            response = self.model.generate_content(prompt)
            
            # Limpiar el texto generado para eliminar encabezados y saltos de línea innecesarios
            analysis_text = response.text.strip() if response.text else ""
            analysis_text = analysis_text.replace("**Descripción Técnica**", "").replace("\n\n", " ").strip()
            
            # Agregar agent_feedback dentro de table_info
            table_info["agent_feedback"] = {
                "analysis": analysis_text,
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
            not_found_tables = []
            processed_tables = set()  # Para llevar un registro de las tablas procesadas exitosamente

            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    table_name = row['table_name']
                    logging.info(f"Procesando tabla: {table_name}")
                    
                    url = self.base_url.format(table_name.lower())
                    result = self.process_url(url)
                    
                    if result.get("name") == "Table" and not result.get("fields"):
                        logging.warning(f"Tabla no encontrada: {table_name}")
                        
                        # Intentar obtener la descripción desde un archivo de texto
                        txt_path = os.path.join('table_descriptions', f'{table_name.lower()}.txt')
                        try:
                            with open(txt_path, 'r', encoding='utf-8') as txt_file:
                                description = txt_file.read().strip()
                                logging.info(f"Descripción obtenida desde {txt_path}: {description}")
                                
                                # Extraer el nombre de la tabla desde la descripción
                                first_line = description.splitlines()[0]
                                extracted_table_name = first_line.split()[0]  # Asume que el nombre de la tabla es la primera palabra
                                result['name'] = extracted_table_name
                                
                                result['description'] = description
                                
                                # Intentar extraer campos y claves foráneas del texto
                                fields, foreign_keys = self.extract_fields_and_keys(description)
                                result['fields'] = fields
                                result['foreign_keys'] = foreign_keys
                                
                                processed_tables.add(table_name)  # Marcar como procesada exitosamente
                                logging.info(f"Tabla {table_name} procesada exitosamente desde archivo de texto.")
                                
                        except FileNotFoundError:
                            logging.error(f"Archivo de descripción no encontrado para la tabla: {table_name}")
                            not_found_tables.append([table_name, row.get('description', '')])
                            continue
                    else:
                        processed_tables.add(table_name)  # Marcar como procesada exitosamente
                        logging.info(f"Tabla {table_name} procesada exitosamente desde URL.")
                    
                    results.append(result)
                    
                    # Guardar resultado individual
                    output_path = os.path.join('output', f'{table_name.lower()}.json')
                    self.save_json(result, output_path)
            
            # Guardar resultado consolidado solo con tablas encontradas
            consolidated = {
                "processed_at": datetime.datetime.now().isoformat(),
                "tables": results
            }
            self.save_json(consolidated, 'output/__consolidated.json')
            
            # Actualizar lista de tablas no encontradas
            if not_found_tables:
                not_found_tables = [t for t in not_found_tables if t[0] not in processed_tables]
                not_found_path = os.path.join('output', '__not_found.csv')
                with open(not_found_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['table_name', 'description'])
                    writer.writerows(not_found_tables)
                logging.info(f"Se guardó la lista de tablas no encontradas en {not_found_path}")
            
            return results
            
        except Exception as e:
            logging.error(f"Error procesando CSV: {str(e)}")
            return {"error": str(e)}

    def extract_fields_and_keys(self, description):
        """Extrae campos y claves foráneas de la descripción del texto"""
        fields = []
        foreign_keys = []
        
        # Dividir el texto en líneas
        lines = description.splitlines()
        
        # Buscar la línea que indica el inicio de la lista de campos
        start_index = None
        for i, line in enumerate(lines):
            if line.startswith("Field\tDescription\tData Element\tData Type"):
                start_index = i + 1
                break
        
        # Si encontramos el inicio de la lista de campos, procesar las líneas siguientes
        if start_index is not None:
            for line in lines[start_index:]:
                # Dividir la línea en columnas
                columns = line.split('\t')
                if len(columns) >= 5:
                    field = {
                        "name": columns[0].strip(),
                        "description": columns[1].strip(),
                        "data_element": columns[2].strip(),
                        "type": columns[3].strip(),
                        "length": columns[4].strip().split('(')[0].strip(),  # Extraer solo la longitud
                        "decimals": columns[4].strip().split('(')[1].strip(')') if '(' in columns[4] else "0"
                    }
                    fields.append(field)
        
        return fields, foreign_keys

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
            
        logging.info("Los resultados se han guardado en el directorio output/")
        
    except Exception as e:
        logging.error(f"Error en la ejecución: {e}")
        raise
    finally:
        logging.info("Finalizando proceso")

if __name__ == "__main__":
    main()