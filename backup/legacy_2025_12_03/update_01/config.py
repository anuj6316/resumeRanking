from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient

class Config:
    CV_COLLECTION = 'cv_embeddings'

    EMBEDDING_MODEL = 'sentence-transformers/all-mpnet-base-v2'
    EMBEDDING_FUNCTION = HuggingFaceEmbeddings(
        model_name = EMBEDDING_MODEL
    )

    QDRANT_CLIENT = QdrantClient(
        url="localhost:6333"
    )

