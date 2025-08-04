# tools_completo.py - VERSIÓN FINAL CORREGIDA
from langchain.tools import tool
from langchain.tools import StructuredTool
from langchain.agents.agent_types import AgentType
from typing import Dict, List, Optional, Any, Union
import json
import logging

from utils.candidatos import SpreadsheetManager
from utils.cv_analyser import CVProcessor
from utils.info_perfil import AIBotTool

logger = logging.getLogger(__name__)

class PathTools:
    @staticmethod
    def run_def_spreadsheet(action: str, phone: Optional[str] = None, candidate_data: Optional[Dict[str, Any]] = None, candidate_id: Optional[str] = None) -> str:
        """
        Ejecuta acciones del spreadsheet manager con parámetros flexibles
        
        Args:
            action (str): Acción a realizar (get_candidate, add_candidate, update_candidate)
            phone (str, optional): Número de teléfono para búsquedas
            candidate_data (Dict, optional): Datos del candidato para agregar/actualizar
            candidate_id (str, optional): ID del candidato para actualizaciones
        """
        try:
            logger.info(f"🔧 Ejecutando spreadsheet - Acción: {action}")
            logger.info(f"📞 Teléfono: {phone}")
            logger.info(f"📋 Datos del candidato: {candidate_data}")
            logger.info(f"🆔 ID del candidato: {candidate_id}")
            
            # Preparar candidate_data según la acción
            if action == "get_candidate":
                # Para búsquedas, usar el teléfono
                if phone:
                    prepared_data = {"phone": phone}
                elif candidate_data and "phone" in candidate_data:
                    prepared_data = candidate_data
                else:
                    return json.dumps({
                        "status": "error",
                        "message": "Número de teléfono requerido para buscar candidato"
                    })
                    
            elif action in ["add_candidate", "update_candidate"]:
                # Para agregar/actualizar, usar candidate_data
                prepared_data = candidate_data or {}
                
            else:
                return json.dumps({
                    "status": "error", 
                    "message": f"Acción no válida: {action}"
                })
            
            # Ejecutar con SpreadsheetManager
            registro = SpreadsheetManager()
            result = registro.run_spreadsheet_manager(action, prepared_data, candidate_id)
            
            logger.info(f"✅ Resultado del spreadsheet: {result[:200]}...")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en run_def_spreadsheet: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Error ejecutando spreadsheet manager: {str(e)}"
            })
    
    # ✅ HERRAMIENTA CORREGIDA - Parámetros más flexibles
    ejecutar_spreadsheet_manager = StructuredTool.from_function(
        func=run_def_spreadsheet,
        name='ejecutar_spreadsheet_manager',
        description='''Gestiona candidatos en Google Sheets.

        Ejemplos de uso:
        - Para buscar candidato: action="get_candidate", phone="51987654321"
        - Para agregar candidato: action="add_candidate", candidate_data={"nombre_completo": "Juan Pérez", "phone": "51987654321", ...}
        - Para actualizar candidato: action="update_candidate", candidate_id="CAND_123", candidate_data={"comentarios": "Actualizado", ...}
        
        Parámetros principales:
        - action: "get_candidate" | "add_candidate" | "update_candidate"
        - phone: número de teléfono (para búsquedas)
        - candidate_data: diccionario con datos del candidato
        - candidate_id: ID del candidato (para actualizaciones)'''
    )

    @staticmethod
    def run_def_analyzer_cv(file_path: str, user_phone: str, user_name: Optional[str] = None) -> str:
        """Ejecuta el procesamiento de CV"""
        try:
            logger.info(f"📄 Procesando CV: {file_path} para {user_phone}")
            procesamiento = CVProcessor()
            return procesamiento.run_analizer_cv(file_path, user_phone, user_name)
        except Exception as e:
            logger.error(f"❌ Error en run_def_analyzer_cv: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Error procesando CV: {str(e)}"
            })

    # Herramienta estructurada
    ejecutar_analyzer_cv = StructuredTool.from_function(
        run_def_analyzer_cv,
        name='ejecutar_analyzer_cv',
        description='Procesa archivos CV (PDF/DOCX) y extrae información del candidato. Requiere file_path y user_phone.'
    )

    @staticmethod
    def run_def_retriever(history_messages: List, question: str) -> str:
        """Ejecuta el retriever cuando el usuario requiere información del perfil del puesto o condiciones del trabajo"""
        try:
            logger.info(f"🔍 Ejecutando retriever para pregunta: {question}")
            retriever = AIBotTool()
            return retriever.run_retriever(history_messages, question)
        except Exception as e:
            logger.error(f"❌ Error en run_def_retriever: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Error en retriever: {str(e)}"
            })

    # Herramienta estructurada
    ejecutar_retriever = StructuredTool.from_function(
        run_def_retriever,
        name='ejecutar_retriever',
        description='Busca información sobre el puesto de Asesor de Ventas Call Center Movistar en la base de conocimientos RAG. Usar cuando el usuario pregunte sobre requisitos, beneficios, horarios, etc.'
    )





































