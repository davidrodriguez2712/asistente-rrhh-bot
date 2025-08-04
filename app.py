
from flask import Flask, request, jsonify
import os
import tempfile
import requests
from pathlib import Path
import time
import logging
import traceback
from threading import Lock

from services.waha import Waha
from agent_completo import AgentPath

# Configurar logging más detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración global
UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

# ✅ NUEVO: Control de mensajes duplicados
processed_messages = set()
processing_lock = Lock()

# Crear directorio de uploads temporales si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def is_duplicate_message(message_id, chat_id, timestamp):
    """Verifica si el mensaje ya fue procesado"""
    message_key = f"{chat_id}_{message_id}_{timestamp}"
    
    with processing_lock:
        if message_key in processed_messages:
            logger.info(f"🚫 Mensaje duplicado detectado: {message_key}")
            return True
        
        # Agregar a la lista de procesados
        processed_messages.add(message_key)
        
        # ✅ LIMPIEZA: Mantener solo los últimos 1000 mensajes para evitar memory leak
        if len(processed_messages) > 1000:
            # Convertir a lista, ordenar y mantener los últimos 500
            messages_list = list(processed_messages)
            processed_messages.clear()
            processed_messages.update(messages_list[-500:])
        
        logger.info(f"✅ Nuevo mensaje agregado: {message_key}")
        return False

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_cv_file(media_url, mime_type, filename):
    """Determina si un archivo es un CV válido basándose en múltiples criterios"""
    
    # Criterio 1: Verificar extensión de la URL
    if media_url:
        url_lower = media_url.lower()
        if any(ext in url_lower for ext in ['.pdf', '.docx', '.doc']):
            logger.info(f"✅ CV detectado por URL: {url_lower}")
            return True
    
    # Criterio 2: Verificar MIME type
    if mime_type:
        mime_lower = mime_type.lower()
        valid_mimes = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-word',
            'application/x-pdf'
        ]
        if any(valid_mime in mime_lower for valid_mime in valid_mimes):
            logger.info(f"✅ CV detectado por MIME: {mime_lower}")
            return True
    
    # Criterio 3: Verificar nombre del archivo
    if filename:
        filename_lower = filename.lower()
        if any(ext in filename_lower for ext in ['.pdf', '.docx', '.doc']):
            logger.info(f"✅ CV detectado por filename: {filename_lower}")
            return True
    
    # Criterio 4: Verificar palabras clave en el nombre
    if filename:
        cv_keywords = ['cv', 'curriculum', 'resume', 'hoja_vida', 'hv']
        filename_lower = filename.lower()
        if any(keyword in filename_lower for keyword in cv_keywords):
            logger.info(f"✅ CV detectado por keywords en filename: {filename_lower}")
            return True
    
    logger.warning(f"❌ No se detectó CV - URL: {media_url}, MIME: {mime_type}, Filename: {filename}")
    return False

def download_media_file(media_url, chat_id):
    """Descarga archivo multimedia desde WAHA"""
    try:
        logger.info(f"📥 Descargando archivo desde: {media_url}")
        # ✅ CORRECCIÓN: Reemplazar localhost con waha en la URL
        if 'localhost:3000' in media_url:
            media_url = media_url.replace('localhost:3000', 'waha:3000')
            logger.info(f"🔄 URL corregida para Docker: {media_url}")
        
        response = requests.get(media_url, timeout=30)
        response.raise_for_status()
        
        # Determinar extensión del archivo
        file_extension = 'pdf'  # Por defecto PDF
        
        # Intentar obtener extensión de la URL
        if '.' in media_url:
            url_parts = media_url.split('.')
            potential_ext = url_parts[-1].lower()
            if potential_ext in ['pdf', 'doc', 'docx']:
                file_extension = potential_ext
        
        # Crear nombre de archivo temporal
        temp_filename = f"cv_{chat_id}_{int(time.time())}.{file_extension}"
        temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)
        
        # Guardar archivo
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"✅ Archivo descargado: {temp_path} ({len(response.content)} bytes)")
        return temp_path
        
    except Exception as e:
        logger.error(f"❌ Error descargando archivo: {e}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

def extract_phone_from_chat_id(chat_id):
    """Extrae el número de teléfono del chat_id"""
    # El chat_id generalmente viene en formato: "1234567890@c.us"
    return chat_id.split('@')[0]

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de verificación de salud"""
    return jsonify({'status': 'healthy', 'service': 'WhatsApp Chatbot'}), 200

@app.route('/test-agent', methods=['GET'])
def test_agent():
    """Endpoint para testear el agente sin WhatsApp"""
    try:
        logger.info("🧪 Iniciando test del agente...")
        
        # Inicializar agente
        agent_path = AgentPath()
        agente, tools = agent_path.crear_agente()
        
        # Mensaje de prueba
        test_message = "TELEFONO_USUARIO: 51987654321 | MENSAJE: Hola, me interesa el puesto de asesor de ventas"
        
        logger.info(f"📝 Procesando mensaje: {test_message}")
        
        # Procesar mensaje
        resultado = agent_path.procesar_mensaje(test_message, agente, tools, [])
        
        response_message = resultado.get("output", "Sin respuesta del agente")
        
        logger.info(f"✅ Respuesta del agente: {response_message}")
        
        return jsonify({
            'status': 'success',
            'message': 'Test del agente completado',
            'agent_response': response_message,
            'tools_count': len(tools)
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error en test del agente: {e}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'Error en test del agente: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500

@app.route('/chatbot/webhook/', methods=['POST'])
def webhook():
    """Webhook principal para recibir mensajes de WhatsApp"""
    try:
        data = request.json
        logger.info(f"📨 Evento recibido: {data}")

        # Validar que tenemos los datos necesarios
        if not data or 'payload' not in data:
            logger.error("❌ Datos inválidos en webhook")
            return jsonify({'status': 'error', 'message': 'Datos inválidos'}), 400

        payload = data['payload']
        chat_id = payload.get('from')
        received_message = payload.get('body', '')
        message_id = payload.get('id', '')
        timestamp = payload.get('timestamp', 0)
        
        if not chat_id:
            logger.error("❌ Chat ID no encontrado")
            return jsonify({'status': 'error', 'message': 'Chat ID no encontrado'}), 400

        # ✅ NUEVO: Verificar si es mensaje duplicado
        if is_duplicate_message(message_id, chat_id, timestamp):
            logger.info("🚫 Mensaje duplicado - ignorando")
            return jsonify({'status': 'success', 'message': 'Mensaje duplicado ignorado'}), 200

        # Ignorar mensajes de grupos
        is_group = '@g.us' in chat_id
        if is_group:
            logger.info(f"📱 Mensaje de grupo ignorado: {chat_id}")
            return jsonify({'status': 'success', 'message': 'Mensaje de grupo ignorado'}), 200

        # Ignorar mensajes propios (enviados por el bot)
        if payload.get('fromMe', False):
            logger.info("🤖 Mensaje propio ignorado")
            return jsonify({'status': 'success', 'message': 'Mensaje propio ignorado'}), 200

        # Inicializar servicios
        logger.info("🔧 Inicializando servicios...")
        waha = Waha()
        
        # Extraer número de teléfono
        user_phone = extract_phone_from_chat_id(chat_id)
        logger.info(f"📞 Teléfono extraído: {user_phone}")

        # Indicar que estamos escribiendo
        waha.start_typing(chat_id=chat_id)

        try:
            # Inicializar agente
            logger.info("🤖 Inicializando agente...")
            agent_path = AgentPath()
            agente, tools = agent_path.crear_agente()
            logger.info(f"✅ Agente inicializado con {len(tools)} herramientas")

            # Verificar si el mensaje contiene un archivo multimedia
            if payload.get('hasMedia', False) and 'mediaUrl' in payload:
                media_url = payload['mediaUrl']
                mime_type = payload.get('media', {}).get('mimetype', '') or payload.get('mimetype', '')
                filename = payload.get('media', {}).get('filename', '') or payload.get('filename', '') or payload.get('body', '')
                
                logger.info(f"📎 Archivo recibido:")
                logger.info(f"   URL: {media_url}")
                logger.info(f"   MIME: {mime_type}")
                logger.info(f"   Filename: {filename}")
                
                # ✅ CORRECCIÓN: Usar función mejorada de detección
                if is_cv_file(media_url, mime_type, filename):
                    logger.info("📄 ¡CV detectado! Iniciando procesamiento...")
                    
                    # Descargar el archivo
                    temp_file_path = download_media_file(media_url, user_phone)
                    
                    if temp_file_path:
                        # Construir mensaje especial para procesamiento de CV
                        cv_message = f"PROCESO_CV: {temp_file_path} | TELEFONO: {user_phone} | MENSAJE: {received_message or filename}"
                        
                        # Obtener historial de mensajes
                        history_messages = waha.get_history_messages(
                            chat_id=chat_id,
                            limit=10
                        )
                        
                        logger.info(f"📋 Procesando CV con mensaje: {cv_message}")
                        
                        # Procesar con el agente
                        resultado = agent_path.procesar_mensaje(
                            cv_message, 
                            agente, 
                            tools, 
                            history_messages
                        )
                        
                        response_message = resultado.get("output", "✅ CV procesado correctamente. Te contactaremos pronto.")
                        
                        # Limpiar archivo temporal
                        try:
                            os.remove(temp_file_path)
                            logger.info(f"🗑️ Archivo temporal eliminado: {temp_file_path}")
                        except:
                            pass
                    else:
                        response_message = "❌ Hubo un problema al descargar tu CV. Por favor, intenta enviarlo nuevamente."
                else:
                    # No es un CV válido
                    logger.warning("❌ Archivo no reconocido como CV")
                    response_message = "📄 Por favor, envía tu CV en formato PDF o Word (.docx). El archivo que enviaste no pudo ser procesado como CV."
            
            else:
                # Mensaje de texto normal
                logger.info(f"💬 Procesando mensaje de texto: {received_message}")
                
                # Obtener historial de mensajes para contexto
                history_messages = waha.get_history_messages(
                    chat_id=chat_id,
                    limit=10
                )
                logger.info(f"📋 Historial obtenido: {len(history_messages)} mensajes")
                
                # Agregar información del teléfono al mensaje para el agente
                message_with_context = f"TELEFONO_USUARIO: {user_phone} | MENSAJE: {received_message}"
                
                logger.info(f"📝 Procesando con contexto: {message_with_context}")
                
                # Procesar mensaje con el agente
                resultado = agent_path.procesar_mensaje(
                    message_with_context,
                    agente,
                    tools,
                    history_messages
                )
                
                response_message = resultado.get("output", "No pude procesar tu mensaje correctamente. ¿Podrías repetirlo?")
                logger.info(f"✅ Respuesta del agente: {response_message}")

        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")
            logger.error(f"❌ Traceback completo: {traceback.format_exc()}")
            response_message = f"❌ Error técnico: {str(e)}. Por favor, intenta de nuevo."

        # Enviar respuesta
        logger.info(f"📤 Enviando respuesta: {response_message}")
        waha.send_message(
            chat_id=chat_id,
            message=response_message
        )

        # Detener indicador de escritura
        waha.stop_typing(chat_id=chat_id)

        return jsonify({'status': 'success', 'message': 'Mensaje procesado'}), 200

    except Exception as e:
        logger.error(f"❌ Error crítico en webhook: {e}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': f'Error interno: {str(e)}'}), 500

@app.route('/send-message', methods=['POST'])
def send_manual_message():
    """Endpoint para enviar mensajes manuales (útil para testing)"""
    try:
        data = request.json
        chat_id = data.get('chat_id')
        message = data.get('message')
        
        if not chat_id or not message:
            return jsonify({'status': 'error', 'message': 'chat_id y message son requeridos'}), 400
        
        waha = Waha()
        waha.send_message(chat_id, message)
        
        return jsonify({'status': 'success', 'message': 'Mensaje enviado'}), 200
        
    except Exception as e:
        logger.error(f"Error enviando mensaje manual: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': 'Endpoint no encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Error interno: {error}")
    return jsonify({'status': 'error', 'message': 'Error interno del servidor'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 Iniciando aplicación en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)