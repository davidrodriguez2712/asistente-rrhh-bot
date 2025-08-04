# candidatos.py - Fix forzado para Pydantic
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

# ✅ CAMBIO DRÁSTICO - Hacer TODOS los campos opcionales
class SpreadsheetInput(BaseModel):
    action: str = Field(description="Acción a realizar")
    candidate_data: Optional[Dict[str, Any]] = Field(default=None, description="Datos del candidato")
    candidate_id: Optional[str] = Field(default=None, description="ID del candidato")

class SpreadsheetManager(BaseTool):
    name: str = 'spreadsheet_manager'
    description: str = 'Gestiona información de candidatos en Google Sheets'
    args_schema: type[BaseModel] = SpreadsheetInput
    spreadsheet_id: str = Field(default_factory=lambda: os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID'))
    credentials_file: Path = Field(default_factory=lambda: Path(os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', './project-asistente-openai-david-aa78b775fd69.json')))
    client: Any = Field(default=None)
    worksheet: Any = Field(default=None)

    def __init__(self):
        super().__init__()
        self.spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
        self.credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE')
        self.client = None
        self.worksheet = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa el cliente de Google Sheets"""
        try:
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_file, scope
            )
            self.client = gspread.authorize(credentials)

            # Abrir la hoja de cálculos
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)

            # Intentar abrir la hoja 'Candidatos', si no existe, crearla
            try:
                self.worksheet = spreadsheet.worksheet('Candidatos')
            except gspread.WorksheetNotFound:
                self.worksheet = spreadsheet.add_worksheet(
                    title='Candidatos',
                    rows=1000,
                    cols=15
                )
                self._setup_headers()
        except Exception as e:
            return f'Error inicializando Google Sheets: {str(e)}'
    
    def _setup_headers(self):
        """Configura los encabezados de la hoja"""
        headers = [
            'ID',
            'Fecha de Contacto',
            'Nombre Completo',
            'Número de WhatsApp',
            'Correo Electrónico',
            'CV Recibido (Sí/No)',
            'Link al CV',
            'Puesto Solicitado',
            'Fuente (Recomendado/Orgánico)',
            'Comentarios del Agente',
            '¿Cumple Perfil? (Sí/No)',
            'Recomendado (Sí/No)',
            'Fase del Proceso',
            'Fecha Evaluación',
            'Evaluador'
        ]

        self.worksheet.update('A1:O1', [headers])

        # Formatear encabezados
        self.worksheet.format('A1:O1', {
            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
        })

    def _generate_candidate_id(self, phone: str) -> str:
        """Genera un ID único para el candidato"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f'CAND_{phone}_{timestamp}'
    
    def _find_candidate_row(self, phone: str) -> Optional[int]:
        """Busca la fila de un candidato por número de teléfono"""
        try:
            phone_column = self.worksheet.col_values(4) # Columna D (número Whatsapp)
            for i, cell_value in enumerate(phone_column[1:], start=2): # Empezar desde la fila 2
                if cell_value == phone:
                    return i
            return None
        except Exception:
            return None

    def _add_candidate(self, candidate_data: Dict[str, Any]) -> str:
        """Añade un nuevo candidato a la hoja"""
        try:
            # Generar ID
            candidate_id = self._generate_candidate_id(candidate_data.get('phone', ''))

            # Preparar datos de la fila
            row_data = [
                candidate_id,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                candidate_data.get('nombre_completo', ''),
                candidate_data.get('phone', ''),
                candidate_data.get('email', ''),
                'Sí' if candidate_data.get('cv_received', False) else 'No',
                candidate_data.get('cv_link', ''),
                candidate_data.get('puesto_solicitado', 'Asesor de Ventas Call Center Movistar'),
                candidate_data.get('fuente', 'Orgánico'),
                candidate_data.get('comentarios', ''),
                candidate_data.get('cumple_perfil', ''),
                candidate_data.get('recomendado', ''),
                'Inicial',
                '',
                'Clara (IA)'
            ]

            # Añadir fila
            self.worksheet.append_row(row_data)

            return f'Candidato añadido exitosamente con ID: {candidate_id}'

        except Exception as e:
            return f'Error añadiendo candidato: {str(e)}'

    def _update_candidate(self, candidate_id: str, candidate_data: Dict[str, Any]) -> str:
        """Actualiza información de un candidato existente"""
        try:
            # Buscar la fila del candidato por ID
            id_column = self.worksheet.col_values(1) # Columna ID
            row_number = None

            for i, cell_value in enumerate(id_column[1:], start=2):
                if cell_value == candidate_id:
                    row_number = i
                    break
            
            if not row_number:
                return f'Candidato con ID {candidate_id} no encontrado'
            
            # Actualizar campos específicos
            updates = []
            
            if 'cv_link' in candidate_data:
                updates.append({
                    'range': f'G{row_number}',
                    'values': [[candidate_data['cv_link']]]
                })
                # ✅ CORRECCIÓN: Si se actualiza cv_link, cambiar cv_recibido a "Sí"
                updates.append({
                    'range': f'F{row_number}',  # Columna F es cv_recibido
                    'values': [['Sí']]
                })
            
            if 'comentarios' in candidate_data:
                updates.append({
                    'range': f'J{row_number}',
                    'values': [[candidate_data['comentarios']]]
                })
            
            if 'cumple_perfil' in candidate_data:
                valor_cumple = 'Sí' if candidate_data['cumple_perfil'] else 'No'
                updates.append({
                    'range': f'K{row_number}',
                    'values': [[valor_cumple]]
                })

            if 'recomendado' in candidate_data:
                updates.append({
                    'range': f'L{row_number}',
                    'values': [['Sí' if candidate_data['recomendado'] else 'No']]
                })
            
            if 'fase_proceso' in candidate_data:
                updates.append({
                    'range': f'M{row_number}',
                    'values': [[candidate_data['fase_proceso']]]
                })
            
            if 'evaluador' in candidate_data:
                updates.append({
                    'range': f'O{row_number}',
                    'values': [[candidate_data['evaluador']]]
                })
                
                # También actualizar fecha de evaluación
                updates.append({
                    'range': f'N{row_number}',
                    'values': [[datetime.now().strftime("%Y-%m-%d %H:%M:%S")]]
                })
            
            # Ejecutar actualizaciones
            for update in updates:
                self.worksheet.update(update['range'], update['values'])
            
            return f"Candidato {candidate_id} actualizado exitosamente"
            
        except Exception as e:
            return f"Error actualizando candidato: {str(e)}"

    def _get_candidate(self, phone: str) -> Dict[str, Any]:
        """Obtiene información de un candidato por teléfono"""
        try:
            row_number = self._find_candidate_row(phone)
            if not row_number:
                return {'status': 'not_found', 'message': 'Candidato no encontrado'}
            
            # Obtener datos de la fila
            row_data = self.worksheet.row_values(row_number)

            # Mapear datos
            candidate_info = {
                "status": "found",
                "id": row_data[0] if len(row_data) > 0 else '',
                "fecha_contacto": row_data[1] if len(row_data) > 1 else '',
                "nombre_completo": row_data[2] if len(row_data) > 2 else '',
                "telefono": row_data[3] if len(row_data) > 3 else '',
                "email": row_data[4] if len(row_data) > 4 else '',
                "cv_recibido": row_data[5] if len(row_data) > 5 else '',
                "cv_link": row_data[6] if len(row_data) > 6 else '',
                "puesto_solicitado": row_data[7] if len(row_data) > 7 else '',
                "fuente": row_data[8] if len(row_data) > 8 else '',
                "comentarios": row_data[9] if len(row_data) > 9 else '',
                "cumple_perfil": row_data[10] if len(row_data) > 10 else '',
                "recomendado": row_data[11] if len(row_data) > 11 else '',
                "fase_proceso": row_data[12] if len(row_data) > 12 else '',
                "fecha_evaluacion": row_data[13] if len(row_data) > 13 else '',
                "evaluador": row_data[14] if len(row_data) > 14 else ''
            }

            return candidate_info
        
        except Exception as e:
            return {'status': 'error', 'message': f'Error obteniendo candidato: {str(e)}'}

    def _run(self, action: str, candidate_data: Optional[Dict[str, Any]] = None, candidate_id: Optional[str] = None) -> str:
        """Método requerido por BaseTool - FORZANDO DEFAULTS"""
        if candidate_data is None:
            candidate_data = {}
        return self.run_spreadsheet_manager(action, candidate_data, candidate_id)

    def run_spreadsheet_manager(self, action: str, candidate_data: Optional[Dict[str, Any]] = None, candidate_id: Optional[str] = None) -> str:
        """Ejecuta toda la acción solicitada - FORZANDO DEFAULTS"""
        try:
            if candidate_data is None:
                candidate_data = {}
                
            if action == 'add_candidate':
                # Verificar si el candidato ya existe
                phone = candidate_data.get('phone', '')
                existing = self._get_candidate(phone)

                if existing.get('status') == 'found':
                    return json.dumps({
                        'status': 'exists',
                        'message': 'El candidato ya existe en el sistema',
                        'candidate_info': existing
                    }, ensure_ascii=False, indent=2)
                else:
                    result = self._add_candidate(candidate_data)
                    return json.dumps({
                        'status': 'success',
                        'message': result
                    }, ensure_ascii=False, indent=2)
            
            elif action == 'update_candidate':
                if not candidate_id:
                    return json.dumps({
                        'status': 'error',
                        'message': 'ID de candidato requerido para actualización'
                    }, ensure_ascii=False, indent=2)
                
                result = self._update_candidate(candidate_id, candidate_data)
                return json.dumps({
                    'status': 'success',
                    'message': result
                }, ensure_ascii=False, indent=2)
            
            elif action == 'get_candidate':
                phone = candidate_data.get('phone', '')
                if not phone:
                    return json.dumps({
                        'status': 'error',
                        'message': 'Número de teléfono requerido para búsqueda'
                    }, ensure_ascii=False, indent=2)
                
                result = self._get_candidate(phone)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            else:
                return json.dumps({
                    'status': 'error',
                    'message': f'Acción no válida: {action}'
                }, ensure_ascii=False, indent=2)
        
        except Exception as e:
            error_result = {
                'status': 'error',
                'message': f'Error en SpreadsheetManager: {str(e)}'
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)