# imports
import logging
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.models import PointStruct
import hashlib
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

from langchain_community.document_loaders import (
    DirectoryLoader,
    PyMuPDFLoader,
    Docx2txtLoader,
)
from core.config import Config

config = Config()

import services.resume_handler as cv
import utils.total_exp_years as exp

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def get_file_hash(file_path):
    """Generate a SHA256 hash of the file content as a unique identifier."""
    try:
        hash_obj = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        hash_digest = hash_obj.hexdigest()[:32]
        return str(uuid.UUID(hash_digest))
    except Exception as e:
        logging.error(f"Failed to compute file hash for {file_path}: {e}")
        raise


def ensure_cv_collection():
    """Ensure the Qdrant collection exists, create if not."""
    try:
        QdrantVectorStore(
            client=config.QDRANT_CLIENT,
            collection_name=config.CV_COLLECTION,
            embedding=config.EMBEDDING_FUNCTION,
        )
        logging.info(f"Collection '{config.CV_COLLECTION}' is already present.")
    except Exception as e:
        config.QDRANT_CLIENT.create_collection(
            collection_name=config.CV_COLLECTION,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
        logging.info(f"New collection '{config.CV_COLLECTION}' created.")
        logging.debug(f"Exception when checking collection: {e}")


def check_duplicate_resume(resume_id):
    """Check if a resume with the given id already exists in the collection."""
    try:
        result = config.QDRANT_CLIENT.retrieve(
            collection_name=config.CV_COLLECTION, ids=[resume_id]
        )
        return len(result) > 0
    except Exception as e:
        logging.error(f"Error checking for duplicate resume: {e}")
        return False


def upload_cv(cv_path):
    ensure_cv_collection()
    if not os.path.exists(cv_path):
        logging.error(f"Path does not exist: {cv_path}")
        return "Path doesn't exist."

    if cv_path.endswith(".pdf"):
        loader = PyMuPDFLoader(cv_path)
    elif cv_path.endswith(".docx") or cv_path.endswith(".doc"):
        loader = Docx2txtLoader(cv_path)
    else:
        logging.error(f"Unsupported file format for file: {cv_path}")
        return "File Format is not supported. Please provide pdf or docx"

    try:
        docs = loader.load()
        cv_text = docs[0].page_content
        resume_id = get_file_hash(cv_path)
        if check_duplicate_resume(resume_id):
            logging.info(
                f"Duplicate resume detected for file: {cv_path}. Skipping upload."
            )
            return f"Duplicate resume detected. {cv_path} was not uploaded again."
        cv_vec = config.EMBEDDING_FUNCTION.embed_query(cv_text)

        work_exp_section = cv.get_work_experience(cv_text)
        exp_section = cv.extract_experience(cv_text)
        complete_exp = work_exp_section + "\n\n" + exp_section
        unique_exp_section = exp.get_unique_experience(complete_exp)
        qdrant_store = QdrantVectorStore(
            client=config.QDRANT_CLIENT,
            collection_name=config.CV_COLLECTION,
            embedding=config.EMBEDDING_FUNCTION,
        )
        payload = {
            "id": resume_id,
            "exp_txt": unique_exp_section,
            "total_exp": exp.total_exp_yrs(unique_exp_section),
            "edu_section": cv.extract_edu(cv_text),
            "skills_section": cv.extract_skills(cv_text),
            "projects_section": cv.extract_projects(cv_text),
            "certification_section": cv.extract_certifications(cv_text),
            "file_path": cv_path,
            "page_content": cv_text,
        }
        # qdrant_store.add_documents(
        #     documents = docs,
        #     ids = [resume_id],
        #     payload = payload
        # )
        point = PointStruct(id=resume_id, vector=cv_vec, payload=payload)

        config.QDRANT_CLIENT.upsert(
            collection_name=config.CV_COLLECTION, points=[point]
        )
        logging.info(f"CV '{cv_path}' uploaded to collection '{config.CV_COLLECTION}'.")
        return f"{cv_path} has been loaded into the {config.CV_COLLECTION} collection"
    except Exception as e:
        logging.error(f"Failed to upload CV '{cv_path}': {e}")
        return f"Failed to upload CV: {e}"


def main():
    upload_cv("/home/anujkumar/resumeRanking/cv/AnuvaGoyal_Latex.pdf")
    pass


if __name__ == "__main__":
    main()
