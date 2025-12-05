from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
import os
from typing import List
from resume_db import upload_cv
import sections_extractor_and_storage as jd
import shutil
from config import Config
from scores import calculate_resume_scores
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader
from llm import ai_res
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

config = Config()
app = FastAPI()
latest_jd_text = None
latest_resume_ids = None
# ...existing code...
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Add CORS middleware - ADD THIS SECTION
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def jd_text(file_path):
    if file_path.endswith(".docx") or file_path.endswith(".doc"):
        from langchain_community.document_loaders import Docx2txtLoader

        loader = Docx2txtLoader(file_path)
    elif file_path.endswith(".pdf"):
        loader = PyMuPDFLoader(file_path)
    else:
        raise ValueError(
            "Unsupported file format. Only .docx, .doc, and .pdf are supported."
        )
    data = loader.load()
    text = ""
    for doc in data:
        text += doc.page_content + "\n\n"  # Add a double newline to separate pages
    return text


@app.get("/total-resumes/")
async def get_total_resumes():
    """
    Endpoint to get the total number of resumes in the Qdrant collection.
    """
    try:
        collection_info = config.QDRANT_CLIENT.get_collection(config.CV_COLLECTION)
        total = collection_info.points_count
        return {"total": total}
    except Exception as e:
        return {"total": 0, "error": str(e)}


@app.post("/upload-cv/")
async def upload_cv_endpoint(files: List[UploadFile] = File(...)):
    """
    Endpoint to upload multiple CV files (PDF or DOCX) to the Qdrant database.
    """
    results = []
    upload_dir = "uploaded_cvs"
    os.makedirs(upload_dir, exist_ok=True)  # Ensure the upload directory exists

    for file in files:
        file_location = os.path.join(upload_dir, file.filename)
        # Save the uploaded file to disk
        with open(file_location, "wb") as f:
            content = await file.read()
            f.write(content)
        # Call the upload_cv function from resume_db.py
        result = upload_cv(file_location)
        results.append({"filename": file.filename, "result": result})

    return JSONResponse(content={"results": results})


global ids


@app.post("/scores/")
async def upload_pdf(file: UploadFile = File(...), n: int = 5):
    # ensure_collection()

    file_location = os.path.join(UPLOAD_DIR, file.filename)
    # Save the file first
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Now process the saved file
    text = jd_text(file_location)
    result = jd.classify_jd(text)

    result_dict = result.dict()
    result_dict["jd_text"] = text

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


@app.post("/query/")
def query(request: QueryRequest, n: int = 5):
    global latest_jd_text, latest_resume_ids
    if not latest_jd_text or not latest_resume_ids:
        return {"error": "No JD uploaded yet. Please upload a JD first."}
    print(latest_resume_ids)
    results = ai_res(request.Query, latest_jd_text, latest_resume_ids[:n])
    return {"results": results}


from fastapi.responses import FileResponse
from fastapi import Request

# ... (keep existing imports)


@app.get("/{filepath:path}")
async def get_file(filepath: str):
    # Security check: only serve files from allowed directories
    allowed_directories = [
        os.path.abspath(os.path.join(UPLOAD_DIR, "..", "cv")),
        os.path.abspath(os.path.join(UPLOAD_DIR, "uploaded_cvs")),
    ]
    requested_path = os.path.abspath(filepath)

    if not any(
        requested_path.startswith(allowed_dir) for allowed_dir in allowed_directories
    ):
        return JSONResponse(status_code=403, content={"error": "Access denied"})

    if not os.path.exists(requested_path):
        return JSONResponse(status_code=404, content={"error": "File not found"})

    return FileResponse(requested_path)


@app.get("/preview-resume/{resume_id}")
async def preview_resume(request: Request, resume_id: str):
    """
    Endpoint to preview a resume by its ID.
    """
    try:
        # Retrieve the resume payload from Qdrant
        retrieved_points = config.QDRANT_CLIENT.retrieve(
            collection_name=config.CV_COLLECTION, ids=[resume_id], with_payload=True
        )

        if not retrieved_points:
            return JSONResponse(status_code=404, content={"error": "Resume not found"})

        # Extract file path from the payload
        file_path = retrieved_points[0].payload.get("file_path")

        if not file_path or not os.path.exists(file_path):
            return JSONResponse(
                status_code=404, content={"error": "Resume file not found on disk"}
            )

        # Read the file content
        text = jd_text(file_path)

        # Construct the file URL
        file_url = str(request.base_url) + file_path

        return {"resume_id": resume_id, "content": text, "file_url": file_url}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    uvicorn.run(app, port=8000, host="localhost", reload=True)
