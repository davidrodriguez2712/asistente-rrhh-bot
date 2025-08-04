# info_perfil.py
import os
from dotenv import load_dotenv
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

class AIBotTool:
    def __init__(self):
        self.chat_model = ChatOpenAI(model='gpt-4o-mini')
        self.retriever = self._build_retriever()

        # Prompt system para el agente RAG
        self.system_template = """
        Eres un asistente virtual especializado en resolver dudas sobre el puesto 'Asesor de Ventas Call Center Movistar'.

        Tu tarea es responder de forma clara, amable y directa, usando el contexto proporcionado. Usa un tono humano, amigable y profesional. Responde siempre en español. Emplea emojis si aportan calidez a la conversación.

        Apóyate exclusivamente en el siguiente contexto para brindar respuestas útiles y veraces:

        <context>
        {context}
        </context>
        """

        self.qa_prompt = ChatPromptTemplate.from_messages([
            ('system', self.system_template),
             MessagesPlaceholder(variable_name= 'messages')
        ])

        self.doc_chain = create_stuff_documents_chain(self.chat_model, self.qa_prompt)

    def _build_retriever(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        persist_directory = os.path.join(base_dir, 'RAG', 'chroma_vectorstore_RAG')
        embedding_model = OpenAIEmbeddings(model='text-embedding-ada-002')

        vector_store = Chroma(
            persist_directory = persist_directory,
            embedding_function = embedding_model
        )
        return vector_store.as_retriever(search_kwargs={'k':30})
    
    def _build_messages(self, history_messages, question):
        messages = []
        for message in history_messages:
            cls = HumanMessage if message.get('fromMe') else AIMessage
            messages.append(cls(content= message.get('body')))
        messages.append(HumanMessage(content= question))
        return messages
    
    def run_retriever(self, history_messages, question):
        context_docs = self.retriever.invoke(question)
        messages = self._build_messages(history_messages, question)

        response = self.doc_chain.invoke({
            'context': context_docs,
            'messages': messages
        })

        return response

































