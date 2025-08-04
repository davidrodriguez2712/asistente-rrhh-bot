# Imports
import os
import json
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

import PyPDF2
from docx import Document
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

import shutil


# Class (basemodel)

class CVProcessorInput(BaseModel):
    file_path: str = Field(description = 'Ruta al archivo CV (PDF o Word)')
    user_phone: str = Field(description = 'Número de teléfono del usuario')
    user_name: Optional[str] = Field(default = None, description = 'Nombre del usuario')

# Class (basetool)

class CVProcessor(BaseTool):
    name: str = 'cv_processor'
    description: str = 'Procesa archivos CV en formato PDF o Word y extrae información relevante'
    args_schema: type[BaseModel] = CVProcessorInput
    storage_path: Path = Field(default_factory=lambda: Path(os.getenv('CV_STORAGE_PATH', './cv_storage/')))

# init
    def __init__(self):
        super().__init__()
        self.storage_path = Path(os.getenv('CV_STORAGE_PATH', './cv_storage/'))
        self.storage_path.mkdir(exist_ok=True) # Ese exist_ok=True: En caso exista, siga la ejecución normalmente

# Función extract text from pdf
# estoy usando el PyPDF2
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extrae texto de un archivo PDF"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ''
                for page in pdf_reader.pages:
                    text += page.extract_text() + '\n'
                return text.strip()
        except Exception as e:
            raise Exception(f'Error al leer PDF: {str(e)}')

# Función extract text from docx
    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extrae texto de un archivo Word"""
        try:
            doc = Document(file_path)
            text = ''
            for paragraph in doc.paragraphs:
                text += paragraph.text + '\n'
            return text.strip()
        except Exception as e:
            raise Exception(f'Error al leer Word: {str(e)}')

# Función save cv file - MODIFICADA para generar URL
    def _save_cv_file(self, original_path: str, user_phone: str) -> Dict[str, str]:
        """Guarda el CV en el directorio de almacenamiento y genera la URL"""
        original_file = Path(original_path)
        file_extension = original_file.suffix
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f'CV_{user_phone}_{timestamp}{file_extension}'
        new_path = self.storage_path / new_filename

        # Copiar archivo
        shutil.copy2(original_path, new_path)

        # ✅ NUEVO: Generar URL para descarga
        # En un entorno real, esto podría ser una URL del servidor web
        cv_url = f"/app/cv_storage/{new_filename}"  # Ruta interna
        
        # Para acceso web (si tienes un servidor web sirviendo los archivos)
        # cv_url = f"https://tu-dominio.com/cvs/{new_filename}"

        return {
            'file_path': str(new_path),
            'cv_url': cv_url,
            'filename': new_filename
        }

# Función  extract cv info
    def _extract_cv_info(self, cv_text: str) -> Dict[str, Any]:
        """Extrae información estructurada del CV usando Langchain/OpenAI"""
        from langchain_openai import ChatOpenAI
        from langchain.prompts import ChatPromptTemplate

        llm = ChatOpenAI(model= 'gpt-4o', temperature = 0)

        prompt = ChatPromptTemplate.from_template("""
        Analiza el siguiente CV y extrae la información en formato JSON:

        CV Text:
        {cv_text}

        Extrae la siguiente información y devuelve solo el JSON:
        {{
            "nombre_completo": "nombre completo del candidato",
            "email": "correo electrónico",
            "telefono": "número de teléfono",
            "experiencia_años": "años de experiencia aproximados",
            "puesto_actual": "puesto o título actual",
            "habilidades": ["lista", "de", "habilidades"],
            "educacion": "nivel educativo más alto",
            "idiomas": ["lista", "de", "idiomas"],
            "ubicacion": "ciudad/país de residencia",
            "resumen_profesional": "breve resumen en 2-3 líneas"
        }}
            """
        )

        chain = prompt | llm
        response = chain.invoke({'cv_text': cv_text})

        try:
            # Intentar parsear JSON de la respuesta
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError('No se encontró JSON válido en la respuesta')
        except Exception as e:
            # Si falla el parsing, devolver estructura básica
            return {
                "nombre_completo": "No extraído",
                "email": "No extraído",
                "telefono": "No extraído",
                "experiencia_años": "No especificado",
                "puesto_actual": "No especificado",
                "habilidades": [],
                "educacion": "No especificado",
                "idiomas": [],
                "ubicacion": "No especificado",
                "resumen_profesional": "Error en extracción automática"
            }

    # ✅ NUEVA FUNCIÓN: Evaluar si cumple el perfil
    def _evaluate_profile_match(self, cv_info: Dict[str, Any], cv_text: str) -> Dict[str, Any]:
        """Evalúa si el candidato cumple con el perfil del puesto"""
        from langchain_openai import ChatOpenAI
        from langchain.prompts import ChatPromptTemplate

        llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)

        prompt = ChatPromptTemplate.from_template("""
        Evalúa si este candidato cumple con el perfil para el puesto de "Asesor de Ventas Call Center Movistar".

        REQUISITOS DEL PUESTO:
        - Educación mínima: Secundaria completa
        - Experiencia previa en ventas por call center o atención al cliente (deseable)
        - Facilidad de comunicación, persuasión y orientación a resultados
        - Manejo básico de computadoras y sistemas
        - Disponibilidad para laborar presencial en Comas, Lima

        INFORMACIÓN DEL CANDIDATO:
        Datos estructurados: {cv_info}
        
        Texto completo del CV: {cv_text}

        Evalúa y responde SOLO con un JSON en este formato:
        {{
            "cumple_perfil": true o false,
            "comentarios": "Justificación detallada de por qué cumple o no cumple el perfil, mencionando aspectos específicos como experiencia, educación, habilidades relevantes, etc."
        }}
        """)

        try:
            chain = prompt | llm
            response = chain.invoke({
                'cv_info': json.dumps(cv_info, ensure_ascii=False),
                'cv_text': cv_text[:2000]  # Limitar texto para evitar tokens excesivos
            })

            # Parsear respuesta JSON
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                evaluation = json.loads(json_match.group())
                return {
                    'cumple_perfil': evaluation.get('cumple_perfil', False),
                    'comentarios': evaluation.get('comentarios', 'No se pudo generar evaluación')
                }
            else:
                return {
                    'cumple_perfil': False,
                    'comentarios': 'Error en el análisis automático del perfil'
                }
        except Exception as e:
            return {
                'cumple_perfil': False,
                'comentarios': f'Error evaluando perfil: {str(e)}'
            }
        
    def _run(self, file_path: str, user_phone: str, user_name: Optional[str] = None) -> str:
        """Método requerido por BaseTool"""
        return self.run_analizer_cv(file_path, user_phone, user_name)

# Función run - MODIFICADA
    def run_analizer_cv(self, file_path: str, user_phone: str, user_name: Optional[str] = None) -> str:
        """Ejecuta el procesamiento del CV"""
        try:
            # Verifica que el archivo existe
            if not os.path.exists(file_path):
                return f'Error: El archivo {file_path} no existe'
            
            # Determinar el tipo de archivo
            file_extension = Path(file_path).suffix.lower()

            if file_extension == '.pdf':
                cv_text = self._extract_text_from_pdf(file_path)
            elif file_extension in ['.docx', '.doc']:
                cv_text = self._extract_text_from_docx(file_path)
            else:
                return f'Error: Formato de archivo no soportado ({file_extension}). Solo PDF y Word'
            
            # ✅ MODIFICADO: Guardar archivo CV y obtener URL
            save_result = self._save_cv_file(file_path, user_phone)

            # Extraer información del CV
            cv_info = self._extract_cv_info(cv_text)
            
            # ✅ NUEVO: Evaluar si cumple el perfil
            profile_evaluation = self._evaluate_profile_match(cv_info, cv_text)
            
            # Completar información del CV
            cv_info['cv_file_path'] = save_result['file_path']
            cv_info['cv_url'] = save_result['cv_url']  # ✅ NUEVO: URL del CV
            cv_info['filename'] = save_result['filename']
            cv_info['processed_date'] = datetime.now().isoformat()
            cv_info['user_phone'] = user_phone
            cv_info['user_name_provided'] = user_name
            
            # ✅ NUEVO: Agregar evaluación del perfil
            cv_info['cumple_perfil'] = profile_evaluation['cumple_perfil']
            cv_info['comentarios_agente'] = profile_evaluation['comentarios']

            # Crear resultado
            result = {
                'status': 'success',
                'message': 'CV procesado exitosamente',
                'cv_info': cv_info,
                'cv_text_preview': cv_text[:500] + "..." if len(cv_text) > 500 else cv_text
            }

            return json.dumps(result, ensure_ascii=False, indent=2)
        
        except Exception as e:
            error_result = {
                'status': 'error',
                'message': f'Error procesando CV: {str(e)}',
                'cv_info': None
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
























