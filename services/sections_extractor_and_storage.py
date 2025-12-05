import os
import uuid
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_community.document_loaders import PyMuPDFLoader, DirectoryLoader
from langchain_huggingface import HuggingFaceEmbeddings

# from langchain_sambanova import ChatSambaNovaCloud
from langchain_google_genai import ChatGoogleGenerativeAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from dotenv import load_dotenv

load_dotenv()


class DocumentSections(BaseModel):
    skills: List[str] = Field(description="List of skills mentioned")
    experience: float = Field(description="Total years of experience mentioned")
    role: str = Field(description="Role or position mentioned")
    education: List[str] = Field(
        description="List of educational qualifications mentioned"
    )
    certification: List[str] = Field(description="List of certifications mentioned")


# Initialize components
sections_parser = PydanticOutputParser(pydantic_object=DocumentSections)

# Prompt for extracting sections from any document
sections_prompt = PromptTemplate(
    template="""
    You are an expert in analyzing documents to extract structured information.

    Extract the following sections from the document below:
    - skills: List of technical skills, programming languages, tools, etc.
    - experience: Total years of experience mentioned (as a number) and if the range is given take the min number of experience
        eg: Experience: 0–1 Year -> here experience will be 0
    - role: Current or target role/position
    - education: Educational qualifications and degrees
    - certification: Professional certifications

    If a section is not mentioned or not applicable, use empty list/string or 0.0 for experience.

    Provide output in this format:

    {format_instructions}

    Document Text:
    {document_text}
    """,
    input_variables=["document_text"],
    partial_variables={
        "format_instructions": sections_parser.get_format_instructions()
    },
)

# Initialize LLM and embeddings
# llm = ChatSambaNovaCloud(model="gpt-oss-120b", temperature=0)
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
embedding_function = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"
)

# Qdrant setup
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "JD_sections"

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collection():
    """Create collection if it doesn't exist"""
    try:
        client.get_collection(COLLECTION_NAME)
    except:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=rest.VectorParams(
                size=768,  # all-mpnet-base-v2 dimension
                distance=rest.Distance.COSINE,
            ),
        )


def load_jds(jds_dir: str) -> List[str]:
    loader = DirectoryLoader(
        path=jds_dir,
        glob="*.pdf",
        loader_cls=PyMuPDFLoader,
    )
    docs = loader.load()

    by_source = {}
    for d in docs:
        src = d.metadata.get("source") or d.metadata.get("file_path") or "unknown"
        by_source.setdefault(src, []).append(d.page_content or "")

    merged = []
    for src, pages in by_source.items():
        full_text = "\n".join(pages).strip()
        merged.append((src, full_text))

    return merged


def classify_jd(jd_text: str):
    """Classify the JDs into the section"""
    chain = sections_prompt | llm | sections_parser
    result = chain.invoke({"document_text": jd_text})
    return result


def process_and_store_jds():
    """Process each JD and store its sections in Qdrant"""
    ensure_collection()
    BASE_DIR = os.path.dirname(__file__)
    JD_DIR = os.path.join(BASE_DIR, "knowledge_base", "JDs")

    jds = load_jds("knowledge_base/JDs")
    print(f"Loaded {len(jds)} JDs")

    for file_path, jd_text in jds:
        classified = classify_jd(jd_text)
        print(f"Classified JD: {os.path.basename(file_path)}")

        embedding = embedding_function.embed_query(jd_text)

        unique_id = str(uuid.uuid4())

        # Prepare payload
        payload = {
            "id": unique_id,
            "file_path": file_path,
            "filename": os.path.basename(file_path),
            "skills": classified.skills,
            "experience": classified.experience,
            "role": classified.role,
            "education": classified.education,
            "certification": classified.certification,
            "resume_text": jd_text,
        }

        point = rest.PointStruct(
            id=unique_id,
            vector=embedding,
            payload=payload,
        )

        client.upsert(collection_name=COLLECTION_NAME, points=[point])
        print("stored js with ID: {unique_id}")


if __name__ == "__main__":
    process_and_store_jds()
