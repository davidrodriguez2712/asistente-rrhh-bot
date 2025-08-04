import requests
import os
import logging
from typing import List, Dict, Any, Optional
import time

# Configurar logging
logger = logging.getLogger(__name__)

class Waha:
    """
    Cliente para interactuar con WAHA (WhatsApp HTTP API)
    Maneja el envío de mensajes, obtención de historial y indicadores de escritura
    """
    
    def __init__(self):
        # Configurar URL base desde variable de entorno o usar localhost
        self.__api_url = os.getenv('WAHA_API_URL', 'http://waha:3000')
        self.__session = os.getenv('WAHA_SESSION', 'default')
        
        # Headers por defecto
        self.__headers = {
            'Content-Type': 'application/json',
        }
        
        # Configurar timeout
        self.__timeout = 30
        
        logger.info(f"WAHA inicializado con URL: {self.__api_url}")

    def send_message(self, chat_id: str, message: str, parse_mode: str = None) -> bool:
        """
        Envía un mensaje de texto a un chat específico
        
        Args:
            chat_id (str): ID del chat (número@c.us)
            message (str): Texto del mensaje
            parse_mode (str): Modo de parsing (MarkdownV2, HTML, etc.)
            
        Returns:
            bool: True si el mensaje se envió correctamente
        """
        url = f'{self.__api_url}/api/sendText'
        
        payload = {
            'session': self.__session,
            'chatId': chat_id,
            'text': message,
        }
        
        if parse_mode:
            payload['parseMode'] = parse_mode
        
        try:
            response = requests.post(
                url=url,
                json=payload,
                headers=self.__headers,
                timeout=self.__timeout
            )
            
            response.raise_for_status()
            logger.info(f"Mensaje enviado exitosamente a {chat_id}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error enviando mensaje a {chat_id}: {e}")
            return False

    def send_file(self, chat_id: str, file_path: str, caption: str = None) -> bool:
        """
        Envía un archivo a un chat específico
        
        Args:
            chat_id (str): ID del chat
            file_path (str): Ruta al archivo
            caption (str): Texto que acompaña al archivo
            
        Returns:
            bool: True si el archivo se envió correctamente
        """
        url = f'{self.__api_url}/api/sendFile'
        
        payload = {
            'session': self.__session,
            'chatId': chat_id,
            'file': file_path,
        }
        
        if caption:
            payload['caption'] = caption
        
        try:
            response = requests.post(
                url=url,
                json=payload,
                headers=self.__headers,
                timeout=self.__timeout
            )
            
            response.raise_for_status()
            logger.info(f"Archivo enviado exitosamente a {chat_id}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error enviando archivo a {chat_id}: {e}")
            return False

    def get_history_messages(self, chat_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de mensajes de un chat
        
        Args:
            chat_id (str): ID del chat
            limit (int): Número máximo de mensajes a obtener
            
        Returns:
            List[Dict]: Lista de mensajes del historial
        """
        url = f'{self.__api_url}/api/{self.__session}/chats/{chat_id}/messages'
        
        params = {
            'limit': limit,
            'downloadMedia': False
        }
        
        try:
            response = requests.get(
                url=url,
                params=params,
                headers=self.__headers,
                timeout=self.__timeout
            )
            
            response.raise_for_status()
            messages = response.json()
            
            logger.info(f"Obtenidos {len(messages)} mensajes del historial de {chat_id}")
            return messages
            
        except requests.RequestException as e:
            logger.error(f"Error obteniendo historial de {chat_id}: {e}")
            return []

    def start_typing(self, chat_id: str) -> bool:
        """
        Inicia el indicador de 'escribiendo...' en un chat
        
        Args:
            chat_id (str): ID del chat
            
        Returns:
            bool: True si se activó correctamente
        """
        url = f'{self.__api_url}/api/startTyping'
        
        payload = {
            'session': self.__session,
            'chatId': chat_id,
        }
        
        try:
            response = requests.post(
                url=url,
                json=payload,
                headers=self.__headers,
                timeout=self.__timeout
            )
            
            response.raise_for_status()
            logger.debug(f"Indicador de escritura iniciado para {chat_id}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error iniciando typing para {chat_id}: {e}")
            return False

    def stop_typing(self, chat_id: str) -> bool:
        """
        Detiene el indicador de 'escribiendo...' en un chat
        
        Args:
            chat_id (str): ID del chat
            
        Returns:
            bool: True si se detuvo correctamente
        """
        url = f'{self.__api_url}/api/stopTyping'
        
        payload = {
            'session': self.__session,
            'chatId': chat_id,
        }
        
        try:
            response = requests.post(
                url=url,
                json=payload,
                headers=self.__headers,
                timeout=self.__timeout
            )
            
            response.raise_for_status()
            logger.debug(f"Indicador de escritura detenido para {chat_id}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error deteniendo typing para {chat_id}: {e}")
            return False

    def get_chat_info(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de un chat específico
        
        Args:
            chat_id (str): ID del chat
            
        Returns:
            Dict: Información del chat o None si hay error
        """
        url = f'{self.__api_url}/api/{self.__session}/chats/{chat_id}'
        
        try:
            response = requests.get(
                url=url,
                headers=self.__headers,
                timeout=self.__timeout
            )
            
            response.raise_for_status()
            chat_info = response.json()
            
            logger.info(f"Información del chat {chat_id} obtenida")
            return chat_info
            
        except requests.RequestException as e:
            logger.error(f"Error obteniendo info del chat {chat_id}: {e}")
            return None

    def get_session_status(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de la sesión de WhatsApp
        
        Returns:
            Dict: Estado de la sesión o None si hay error
        """
        url = f'{self.__api_url}/api/sessions/{self.__session}'
        
        try:
            response = requests.get(
                url=url,
                headers=self.__headers,
                timeout=self.__timeout
            )
            
            response.raise_for_status()
            status = response.json()
            
            logger.info(f"Estado de sesión: {status.get('status', 'unknown')}")
            return status
            
        except requests.RequestException as e:
            logger.error(f"Error obteniendo estado de sesión: {e}")
            return None

    def send_reaction(self, chat_id: str, message_id: str, emoji: str) -> bool:
        """
        Envía una reacción a un mensaje específico
        
        Args:
            chat_id (str): ID del chat
            message_id (str): ID del mensaje
            emoji (str): Emoji de reacción
            
        Returns:
            bool: True si la reacción se envió correctamente
        """
        url = f'{self.__api_url}/api/sendReaction'
        
        payload = {
            'session': self.__session,
            'chatId': chat_id,
            'messageId': message_id,
            'reaction': emoji
        }
        
        try:
            response = requests.post(
                url=url,
                json=payload,
                headers=self.__headers,
                timeout=self.__timeout
            )
            
            response.raise_for_status()
            logger.info(f"Reacción {emoji} enviada al mensaje {message_id}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error enviando reacción: {e}")
            return False

    def check_connection(self) -> bool:
        """
        Verifica si la conexión con WAHA está funcionando
        
        Returns:
            bool: True si la conexión es exitosa
        """
        try:
            status = self.get_session_status()
            if status and status.get('status') in ['WORKING', 'CONNECTED']:
                logger.info("Conexión con WAHA verificada exitosamente")
                return True
            else:
                logger.warning(f"WAHA no está conectado. Estado: {status}")
                return False
                
        except Exception as e:
            logger.error(f"Error verificando conexión: {e}")
            return False

    def wait_for_connection(self, max_attempts: int = 10, delay: int = 5) -> bool:
        """
        Espera hasta que WAHA esté conectado
        
        Args:
            max_attempts (int): Número máximo de intentos
            delay (int): Segundos entre intentos
            
        Returns:
            bool: True si se conectó exitosamente
        """
        for attempt in range(max_attempts):
            if self.check_connection():
                return True
            
            logger.info(f"Intento {attempt + 1}/{max_attempts} - Esperando conexión...")
            time.sleep(delay)
        
        logger.error("No se pudo establecer conexión con WAHA")
        return False

    def format_phone_number(self, phone: str) -> str:
        """
        Formatea un número de teléfono para uso con WhatsApp
        
        Args:
            phone (str): Número de teléfono
            
        Returns:
            str: Número formateado (ej: 51987654321@c.us)
        """
        # Remover caracteres no numéricos
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # Si no tiene código de país, asumir Perú (+51)
        if len(clean_phone) == 9:
            clean_phone = '51' + clean_phone
        
        return f"{clean_phone}@c.us"