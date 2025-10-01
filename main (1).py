from qdrant_client.http import models as rest
from sections_extractor_and_storage import classify_jd, embedding_function, client, COLLECTION_NAME, ensure_collection
from langchain_community.document_loaders import PyMuPDFLoader
from scores import calculate_resume_scores
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import resume_database as db
import shutil
import os
import uuid
from pydantic import BaseModel
from typing import List
from llm import ai_res
app = FastAPI()

latest_jd_text = None
latest_resume_ids = None
# ...existing code...
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(UPLOAD_DIR, exist_ok=True)

def jd_text(file_path):
    if file_path.endswith('.docx') or file_path.endswith('.doc'):
        from langchain_community.document_loaders import Docx2txtLoader
        loader = Docx2txtLoader(file_path)
    if file_path.endswith('.pdf'):
        loader = PyMuPDFLoader(file_path)
    data = loader.load()
    text = ""
    for doc in data:
        text += doc.page_content + "\n\n"  # Add a double newline to separate pages
    return text

global ids
@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...), n: int = 5):
    ensure_collection()
    
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    # Save the file first
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Now process the saved file
    text = jd_text(file_location)
    result = classify_jd(text)
    embedding = embedding_function.embed_query(text)
    unique_id = str(uuid.uuid4())
    payload = {
        "id": unique_id,
        "file_path": file_location,
        "filename": os.path.basename(file_location),
        "skills": result.skills,
        "experience": result.experience,
        "role": result.role,
        "education": result.education,
        "certification": result.certification,
        "jd_text": text
    }
    result_dict = result.dict()
    result_dict['jd_text'] = text
    point = rest.PointStruct(
        id=unique_id,
        vector=embedding,
        payload=payload,
    )
    
    client.upsert(collection_name=COLLECTION_NAME, points=[point])
    print("stored js with ID: {unique_id}")
    print(result)
    ans = calculate_resume_scores(result_dict)
    print(list(ans.keys()))
    ids = list(ans.keys())[:n]
    # Store latest JD text and resume IDs for query endpoint
    global latest_jd_text, latest_resume_ids
    latest_jd_text = text
    latest_resume_ids = ids
    return ans

class QueryRequest(BaseModel):
    Query: str

@app.post('/query/')
def query(request: QueryRequest, n: int = 5):
    global latest_jd_text, latest_resume_ids
    if not latest_jd_text or not latest_resume_ids:
        return {"error": "No JD uploaded yet. Please upload a JD first."}
    print(latest_resume_ids)
    results = ai_res(request.Query, latest_jd_text, latest_resume_ids[:n])
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        port=8000,
        host="localhost",
        reload=True
    )