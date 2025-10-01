import os
from dotenv import load_dotenv

class Config:
    RESUME_DIR = "resumes"
    JD_DIR = "jd"
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RESUME_COLLECTION = "resumes_parse"
    JD_COLLECTION = "jd_collection"
    EMBEDDING_MODEL = "sentence-transformers/all-MPNet-base-v2"

    # qdrant config
    