
# agent_completo.py - Super limpio sin referencias JSON problemáticas

import re
import json
import logging
import traceback
from time import sleep
from langchain.agents import (
    AgentExecutor,
    create_tool_calling_agent
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

from dotenv import load_dotenv
load_dotenv()

from tools_completo import PathTools

# Configurar logging detallado
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AgentPath:
    def __init__(self):
        try:
            logger.info("🤖 Inicializando AgentPath...")
            self.llm = ChatOpenAI(model='gpt-4o-mini')
            self.tool = PathTools()
            logger.info("✅ AgentPath inicializado correctamente")
        except Exception as e:
            logger.error(f"❌ Error inicializando AgentPath: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise

    def crear_agente(self):
        try:
            logger.info("🔧 Creando agente...")
            
            tools = [
                PathTools.ejecutar_spreadsheet_manager,
                PathTools.ejecutar_analyzer_cv,
                PathTools.ejecutar_retriever
            ]
            logger.info(f"📦 {len(tools)} herramientas cargadas")

            llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
            logger.info("🧠 LLM inicializado")

            # ✅ PROMPT CORREGIDO - Sin revelar perfil + respuesta estándar entrevistas
            prompt = ChatPromptTemplate.from_messages([
                (
                    'system', 
                    """
                    Eres Clara, asistente virtual de recursos humanos de Vego Comunicaciones.
                    
                    Tu trabajo es ayudar a candidatos interesados en el puesto de Asesor de Ventas Call Center Movistar.

                    TAREAS PRINCIPALES:
                    1. Responder preguntas sobre el puesto usando ejecutar_retriever
                    2. Procesar CVs cuando contengan el patrón PROCESO_CV
                    3. Consultar información de candidatos usando ejecutar_spreadsheet_manager
                    4. Mantener conversaciones amables y profesionales

                    COMPORTAMIENTO:
                    - Responde siempre en español
                    - Sé amable, cálida y profesional
                    - Usa emojis moderadamente
                    - No te presentes repetidamente como Clara
                    - Ayuda y facilita la postulación

                    FLUJO INTELIGENTE DE CV:
                    1. SIEMPRE verifica primero si el usuario ya está registrado usando ejecutar_spreadsheet_manager
                    2. Si el usuario YA TIENE CV procesado (cv_link no vacío O cv_recibido = "Sí"):
                    - NO menciones el CV nuevamente
                    - NO pidas CV
                    - Solo responde sus preguntas normalmente
                    3. Si el usuario NO tiene CV procesado (cv_link vacío Y cv_recibido = "No"):
                    - Si pregunta sobre postulación: pide el CV
                    - Si hace preguntas generales: responde y OPCIONALMENTE menciona que puede postularse enviando su CV
                    4. Solo procesa CV si el mensaje ACTUAL contiene "PROCESO_CV:"

                    MENSAJES SEGÚN ESTADO DEL CANDIDATO:

                    CANDIDATO CON CV YA PROCESADO:
                    - Saludar normalmente sin mencionar CV
                    - Ejemplo: "¡Hola [Nombre]! 😊 ¿En qué puedo ayudarte hoy?"

                    CANDIDATO SIN CV:
                    - Para postulación: "¡Perfecto! Para procesar tu postulación, necesito que me envíes tu CV en formato PDF o Word (.docx). Una vez que lo reciba, extraeré automáticamente toda tu información y te confirmaré tu registro. 📄✨"
                    - Para preguntas generales: Responder la pregunta + "Si deseas postularte, puedes enviarme tu CV cuando gustes. 😊"

                    CANDIDATO NUEVO (no registrado):
                    - Saludar y preguntar si desea información del puesto o postularse

                    🚫 REGLAS PROHIBIDAS - NUNCA HAGAS ESTO:
                    1. NUNCA menciones si el candidato "cumple" o "no cumple" con el perfil
                    2. NUNCA digas "has sido evaluado y cumples con el perfil"
                    3. NUNCA menciones "recomendado" o "no recomendado"
                    4. NUNCA reveles información de evaluación interna
                    5. NUNCA uses frases como "cumples con el perfil", "no cumples", "eres apto", "no eres apto"

                    📞 RESPUESTA ESTÁNDAR PARA ENTREVISTAS:
                    Cuando pregunten sobre entrevistas, citas, o siguientes pasos, SIEMPRE responde:
                    "Se comunicarán contigo una vez que la líder de RRHH haya revisado tu CV para agendar una entrevista. 📅 Mientras tanto, si tienes más preguntas sobre el puesto, ¡estaré encantada de ayudarte! 😊"

                    ⚠️ REGLAS CRÍTICAS:

                    1. VERIFICACIÓN OBLIGATORIA:
                    - SIEMPRE usa ejecutar_spreadsheet_manager con get_candidate al inicio
                    - Revisa cv_link Y cv_recibido para determinar estado del CV

                    2. PROCESAMIENTO DE CV:
                    - SOLO usa ejecutar_analyzer_cv si el mensaje ACTUAL contiene exactamente "PROCESO_CV:"
                    - NUNCA adivines nombres de archivos
                    - NUNCA proceses CV basándote en el historial

                    3. DETERMINACIÓN DE ESTADO DE CV:
                    - CV PROCESADO: cv_link no vacío O cv_recibido = "Sí"
                    - CV NO PROCESADO: cv_link vacío Y cv_recibido = "No"

                    4. CONFIDENCIALIDAD:
                    - NUNCA reveles evaluaciones internas
                    - NUNCA menciones cumplimiento de perfil
                    - Mantén información de evaluación completamente confidencial

                    INSTRUCCIONES ESPECÍFICAS DE HERRAMIENTAS:

                    🔧 Para ejecutar_spreadsheet_manager:
                    - SIEMPRE verificar estado del candidato primero
                    - action="get_candidate", phone="numero_telefono"
                    - Usar resultado para determinar flujo de conversación

                    📄 Para ejecutar_analyzer_cv:
                    - SOLO usar cuando input ACTUAL contenga "PROCESO_CV:"
                    - NUNCA usar basándose en historial

                    🔍 Para ejecutar_retriever:
                    - Para preguntas sobre puesto, requisitos, beneficios, horarios
                    - Usar cuando usuario pregunte información específica del trabajo

                    REGLAS IMPORTANTES:
                    - SOLO procesa CV si input ACTUAL contiene "PROCESO_CV:"
                    - Para preguntas del puesto usa ejecutar_retriever
                    - SIEMPRE verifica estado del candidato antes de pedir CV
                    - No repitas solicitudes de CV si ya fue procesado
                    - NUNCA menciones evaluaciones o cumplimiento de perfil
                    - Para preguntas sobre entrevistas, usa la respuesta estándar
                    - Extrae teléfono del patrón TELEFONO_USUARIO: número en el input

                    Mantén las conversaciones fluidas, naturales y completamente confidenciales sobre evaluaciones internas.
                    """
                ),
                ('placeholder', '{chat_history}'),
                ('human', '{input}'),
                ('placeholder', '{agent_scratchpad}'),
            ])
            logger.info("📝 Prompt configurado")

            agent = create_tool_calling_agent(
                llm=llm,
                tools=tools,
                prompt=prompt,
            )
            logger.info("✅ Agente creado exitosamente")

            return agent, tools
            
        except Exception as e:
            logger.error(f"❌ Error creando agente: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise
    
    def _extract_cv_info_from_input(self, input_message):
        """Extrae información del CV desde el mensaje de entrada"""
        try:
            cv_pattern = r"PROCESO_CV:\s*([^|]+)\s*\|\s*TELEFONO:\s*([^|]+)\s*\|\s*MENSAJE:\s*(.*)"
            match = re.search(cv_pattern, input_message)
            
            if match:
                file_path = match.group(1).strip()
                phone = match.group(2).strip()
                user_message = match.group(3).strip()
                logger.info(f"📎 CV detectado: {file_path}, teléfono: {phone}")
                return {
                    'is_cv': True,
                    'file_path': file_path,
                    'phone': phone,
                    'message': user_message
                }
            return {'is_cv': False}
        except Exception as e:
            logger.error(f"❌ Error extrayendo info CV: {e}")
            return {'is_cv': False}
    
    def _extract_phone_from_input(self, input_message):
        """Extrae el número de teléfono del mensaje de entrada"""
        try:
            phone_pattern = r"TELEFONO_USUARIO:\s*([^|]+)\s*\|\s*MENSAJE:\s*(.*)"
            match = re.search(phone_pattern, input_message)
            
            if match:
                phone = match.group(1).strip()
                message = match.group(2).strip()
                logger.info(f"📞 Teléfono extraído: {phone}")
                return {
                    'phone': phone,
                    'message': message
                }
            return {'phone': None, 'message': input_message}
        except Exception as e:
            logger.error(f"❌ Error extrayendo teléfono: {e}")
            return {'phone': None, 'message': input_message}
    
    def _format_chat_history(self, history_messages):
        """Convierte el historial en objetos de mensaje de LangChain"""
        try:
            formatted_messages = []
            
            if not history_messages:
                return []
            
            # Procesar solo los últimos 5 mensajes para no sobrecargar
            recent_messages = history_messages[-5:] if len(history_messages) > 5 else history_messages
            
            for message in recent_messages:
                if not message.get('body'):
                    continue
                    
                body = message.get('body', '').strip()
                if not body:
                    continue
                
                # ✅ FILTRAR nombres de archivos del historial para evitar confusión
                if body.endswith('.pdf') or body.endswith('.docx') or body.endswith('.doc'):
                    logger.info(f"🚫 Filtrando nombre de archivo del historial: {body}")
                    continue
                
                # Determinar si es del usuario o del asistente
                if message.get('fromMe', False):
                    # Mensaje del bot (asistente)
                    formatted_messages.append(AIMessage(content=body))
                else:
                    # Mensaje del usuario
                    formatted_messages.append(HumanMessage(content=body))
            
            logger.info(f"📋 Historial formateado: {len(formatted_messages)} mensajes válidos")
            return formatted_messages
            
        except Exception as e:
            logger.warning(f"⚠️ Error formateando historial: {e}")
            return []

    def procesar_cv_con_evaluacion(self, cv_result, user_phone):
        """Procesa el resultado del CV y registra/actualiza al candidato con todos los campos"""
        try:
            logger.info("🔄 Iniciando procesamiento completo del CV...")
            
            # Parsear resultado del CV
            cv_data = json.loads(cv_result)
            
            if cv_data.get('status') != 'success':
                logger.error("❌ Error en procesamiento de CV")
                return None
            
            cv_info = cv_data.get('cv_info', {})
            logger.info(f"📋 CV info extraída: {cv_info.get('nombre_completo', 'N/A')}")
            
            # Verificar si el candidato ya existe
            existing_check = self.tool.run_def_spreadsheet(
                action="get_candidate",
                candidate_data={"phone": user_phone}
            )
            
            existing_data = json.loads(existing_check)
            logger.info(f"🔍 Verificación existencia: {existing_data.get('status')}")
            
            if existing_data.get('status') == 'found':
                # Candidato existe - actualizar con nueva información del CV
                candidate_id = existing_data.get('id')
                logger.info(f"🔄 Actualizando candidato existente: {candidate_id}")
                
                update_data = {
                    'cv_link': cv_info.get('cv_url', ''),
                    'comentarios': cv_info.get('comentarios_agente', ''),
                    'cumple_perfil': cv_info.get('cumple_perfil', False),
                    'recomendado': cv_info.get('cumple_perfil', False),
                    'evaluador': 'Clara (IA)',
                    'fase_proceso': 'CV Evaluado'
                }
                
                update_result = self.tool.run_def_spreadsheet(
                    action="update_candidate",
                    candidate_data=update_data,
                    candidate_id=candidate_id
                )
                
                logger.info("✅ Candidato actualizado exitosamente")
                return {
                    'success': True,
                    'candidate_id': candidate_id,
                    'nombre': cv_info.get('nombre_completo', 'Usuario'),
                    'action': 'updated'
                }
                
            else:
                # Candidato nuevo - registrar completo
                logger.info("➕ Registrando candidato nuevo...")
                
                candidate_data = {
                    'nombre_completo': cv_info.get('nombre_completo', ''),
                    'phone': user_phone,
                    'email': cv_info.get('email', ''),
                    'cv_received': True,
                    'cv_link': cv_info.get('cv_url', ''),
                    'puesto_solicitado': 'Asesor de Ventas Call Center Movistar',
                    'habilidades': ', '.join(cv_info.get('habilidades', [])),
                    'educacion': cv_info.get('educacion', ''),
                    'experiencia_años': cv_info.get('experiencia_años', ''),
                    'ubicacion': cv_info.get('ubicacion', ''),
                    'comentarios': cv_info.get('comentarios_agente', ''),
                    'cumple_perfil': cv_info.get('cumple_perfil', False),
                    'recomendado': cv_info.get('cumple_perfil', False),
                    'fuente': 'Orgánico'
                }
                
                add_result = self.tool.run_def_spreadsheet(
                    action="add_candidate",
                    candidate_data=candidate_data
                )
                
                result_data = json.loads(add_result)
                
                if result_data.get('status') == 'success':
                    # Extraer ID del candidato del mensaje de éxito
                    success_message = result_data.get('message', '')
                    id_match = re.search(r'ID: (CAND_\w+)', success_message)
                    candidate_id = id_match.group(1) if id_match else 'ID_NO_ENCONTRADO'
                    
                    logger.info(f"✅ Candidato registrado exitosamente: {candidate_id}")
                    return {
                        'success': True,
                        'candidate_id': candidate_id,
                        'nombre': cv_info.get('nombre_completo', 'Usuario'),
                        'action': 'created'
                    }
                else:
                    logger.error("❌ Error registrando candidato")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error en procesamiento completo: {str(e)}")
            return None
    
    def procesar_mensaje(self, msg, agente, tools, history_messages=None):
        """Procesa el mensaje recibido vía WhatsApp y llama a la herramienta correcta."""
        try:
            logger.info(f"📝 Iniciando procesamiento del mensaje: {msg}")
            
            # ✅ VERIFICACIÓN MEJORADA - Solo procesar CV si está en el mensaje ACTUAL
            if "PROCESO_CV:" in msg:
                logger.info("📎 Detectado procesamiento de CV - Modo automático")
                
                # Extraer información del CV
                cv_info = self._extract_cv_info_from_input(msg)
                if not cv_info.get('is_cv'):
                    return {"output": "❌ Error extrayendo información del CV"}
                
                file_path = cv_info['file_path']
                user_phone = cv_info['phone']
                user_name = cv_info.get('message', '').split('.')[0]
                
                logger.info(f"📋 Procesando CV: {file_path} para {user_phone}")
                
                # Paso 1: Procesar CV con analyzer
                cv_result = self.tool.run_def_analyzer_cv(
                    file_path=file_path,
                    user_phone=user_phone,
                    user_name=user_name
                )
                
                # Paso 2: Registrar/actualizar candidato completo
                process_result = self.procesar_cv_con_evaluacion(cv_result, user_phone)
                
                if process_result and process_result.get('success'):
                    candidate_id = process_result['candidate_id']
                    nombre = process_result['nombre']
                    action = process_result['action']
                    
                    if action == 'created':
                        response = f"¡Gracias, {nombre}! 😊 He recibido tu CV y lo he procesado exitosamente. Tu información ha sido registrada en nuestro sistema con el ID: **{candidate_id}**. Si tienes alguna pregunta adicional sobre el proceso, ¡no dudes en decírmelo! 🌟"
                    else:
                        response = f"¡Hola nuevamente, {nombre}! 😊 He actualizado tu información con el nuevo CV. Tu ID de candidato es: **{candidate_id}**. ¡Gracias por mantener tu perfil actualizado! 🌟"
                    
                    return {"output": response}
                else:
                    return {"output": "❌ Hubo un problema procesando tu CV. Por favor, intenta nuevamente."}
            
            # ✅ PARA MENSAJES NORMALES - Procesar con agente normal
            logger.info("💬 Procesando mensaje normal (no es CV)")
            
            agent_executor = AgentExecutor.from_agent_and_tools(
                agent=agente,
                tools=tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=3,
            )
            logger.info("🔧 AgentExecutor creado")

            # Preparar el input para el agente
            executor_prompt = {
                "input": msg
            }

            # Formatear historial correctamente
            if history_messages:
                try:
                    formatted_history = self._format_chat_history(history_messages)
                    executor_prompt["chat_history"] = formatted_history
                    logger.info(f"📋 Historial formateado correctamente: {len(formatted_history)} mensajes")
                except Exception as e:
                    logger.warning(f"⚠️ Error formateando historial: {e}")
                    executor_prompt["chat_history"] = []
            else:
                executor_prompt["chat_history"] = []

            logger.info("🚀 Ejecutando agente...")
            resultado = agent_executor.invoke(executor_prompt)
            logger.info(f"✅ Agente ejecutado. Output: {resultado.get('output', 'Sin output')}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error en procesar_mensaje: {e}")
            logger.error(f"❌ Traceback completo: {traceback.format_exc()}")
            
            # Respuestas de fallback específicas
            if "chat_history" in str(e):
                error_msg = "❌ Error en historial de chat. Intenta enviar tu mensaje nuevamente."
            elif "OpenAI" in str(e):
                error_msg = "❌ Error de conexión con OpenAI. Verifica tu API key."
            elif "Google" in str(e) or "Sheets" in str(e):
                error_msg = "❌ Error de conexión con Google Sheets. Verifica las credenciales."
            elif "RAG" in str(e) or "retriever" in str(e):
                error_msg = "❌ Error en el sistema de búsqueda. La base de conocimientos no está disponible."
            elif "CV" in str(e):
                error_msg = "❌ Error procesando CV. Intenta enviar el archivo nuevamente."
            else:
                error_msg = f"❌ Error técnico: {str(e)}. Por favor, intenta nuevamente."
            
            return {
                "output": error_msg
            }