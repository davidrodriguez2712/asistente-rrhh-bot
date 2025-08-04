## AQUI LA LÓGICA DEL RAG
import os

from langchain_community. document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from dotenv import load_dotenv
load_dotenv()

if __name__ == '__main__':
    # Paso 1: Document Loader
    path = 'Base_de_Conocimientos/PERFIL_DE_PUESTO_ASESOR_DE_VENTAS_CALL_CENTER.pdf'
    loader = PyPDFLoader(path)
    documentos = loader.load() # extrae los documentos del PDF

    # Paso 2: Chunking / Documment Splitting
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1000,
        chunk_overlap = 200,
    )
    chunks = text_splitter.split_documents(
        documents=documentos
    )

    # Paso 3: Embeddings - Convertir los documentos a Embeddings, convertir a números
    embedding_model = OpenAIEmbeddings(model='text-embedding-ada-002')

    # Paso 4: VectorStore - Crear la Base de Datos Vectorial
    directorio_de_vectores = 'chroma_vectorstore_RAG'

    vectorstore = Chroma.from_documents(
        documents= chunks,
        embedding= embedding_model,
        persist_directory = directorio_de_vectores
    )







































