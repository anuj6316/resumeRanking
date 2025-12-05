# -*- coding: utf-8 -*-
"""
Main FastAPI application for the Resume Ranking System.
"""

# --------------------------------------------------------------------------
# Imports
# --------------------------------------------------------------------------
import os
import shutil
import uvicorn
import glob
from typing import List

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader

# Local application imports
from core.config import Config
from database.resume_db import upload_cv
import services.sections_extractor_and_storage as jd
from services.scoring.scores import calculate_resume_scores
from services.llm.llm import ai_res, generate_and_save_report
from datetime import datetime
# --------------------------------------------------------------------------
# Configuration and Global State
# --------------------------------------------------------------------------
config = Config()
app = FastAPI(title="Resume Ranking API", version="1.0.0")

# Base directory of the application
APP_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(APP_DIR, "uploaded_cvs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Global State ---
# NOTE: In a production environment, this state should be managed in a
# more robust way, e.g., using a database, cache, or a dedicated state manager.
latest_jd_text: str | None = None
latest_resume_ids: List[str] | None = None
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Middleware
# --------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Pydantic Models
# --------------------------------------------------------------------------
class QueryRequest(BaseModel):
    """Request model for the /query/ endpoint."""

    Query: str


# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------
def get_document_text(file_path: str) -> str:
    """
    Load text from a .pdf, .docx, or .doc file.
    """
    if file_path.lower().endswith((".docx", ".doc")):
        loader = Docx2txtLoader(file_path)
    elif file_path.lower().endswith(".pdf"):
        loader = PyMuPDFLoader(file_path)
    elif file_path.lower().endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError(
            "Unsupported file format. Only .docx, .doc, .pdf, and .txt are supported."
        )

    data = loader.load()
    return "\n\n".join(doc.page_content for doc in data)


# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------
@app.get("/total-resumes/", summary="Get total number of resumes")
async def get_total_resumes():
    """
    Endpoint to get the total number of resumes in the Qdrant collection.
    """
    try:
        collection_info = config.QDRANT_CLIENT.get_collection(config.CV_COLLECTION)
        total = collection_info.points_count
        return {"total": total}
    except Exception as e:
        # Log the error for debugging
        print(f"Error getting total resumes: {e}")
        return JSONResponse(status_code=500, content={"total": 0, "error": str(e)})


@app.post("/upload-cv/", summary="Upload one or more resumes")
async def upload_cv_endpoint(
    files: List[UploadFile] = File(...), clear_collection: bool = False
):
    """
    Endpoint to upload multiple CV files (PDF or DOCX) to the Qdrant database.
    Each file is saved to 'uploaded_cvs' and then processed.
    """
    if clear_collection:
        config.QDRANT_CLIENT.delete_collection(collection_name=config.CV_COLLECTION)
    results = []
    for file in files:
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        try:
            # Save the uploaded file to disk
            with open(file_location, "wb") as f:
                f.write(await file.read())

            # Process and upload the CV to the vector database
            result = upload_cv(file_location)
            results.append(
                {"filename": file.filename, "status": "success", "detail": result}
            )
        except Exception as e:
            results.append(
                {"filename": file.filename, "status": "error", "detail": str(e)}
            )

    return JSONResponse(content={"results": results})


@app.post("/scores/", summary="Calculate resume scores against a JD")
async def get_resume_scores(file: UploadFile = File(...), n: int = 5):
    """
    Upload a Job Description, process it, and return ranked resume scores.
    """
    global latest_jd_text, latest_resume_ids

    jd_file_location = os.path.join(APP_DIR, file.filename)

    try:
        # Save the JD file
        with open(jd_file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process the saved file
        text = get_document_text(jd_file_location)
        result = jd.classify_jd(text)

        result_dict = result.dict()
        result_dict["jd_text"] = text

        # Calculate scores and get top N
        all_scores = calculate_resume_scores(result_dict)
        top_n_ids = list(all_scores.keys())

        # Store state for the /query endpoint
        latest_jd_text = text
        latest_resume_ids = top_n_ids

        # Return only the top N scores
        top_scores = {resume_id: all_scores[resume_id] for resume_id in top_n_ids}

        return JSONResponse(content=top_scores)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        # Clean up the uploaded JD file
        if os.path.exists(jd_file_location):
            os.remove(jd_file_location)


@app.post("/query/", summary="Query top resumes with an LLM")
def query_resumes_with_llm(request: QueryRequest, n: int = 5):
    """
    Ask a natural language question about the top-ranked resumes for the latest JD.
    """
    if not latest_jd_text or not latest_resume_ids:
        raise HTTPException(
            status_code=400,
            detail="No JD has been processed. Please use the /scores endpoint first.",
        )

    # Ensure n is not greater than the number of available IDs
    ids_to_query = latest_resume_ids[:n]

    result = ai_res(request.Query, latest_jd_text, ids_to_query)
    # 1. Define a directory to store the final reports
    reports_dir = os.path.join(APP_DIR, "final_reports")
    os.makedirs(reports_dir, exist_ok=True)

    # 2. Create a unique filename using a timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.join(reports_dir, f"resume_analysis_report_{timestamp}.md")

    # 3. Write the markdown report to the file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(result["summary_report"])
        print(f"Successfully saved report to {file_path}")
    except Exception as e:
        print(f"Error saving report: {e}")
    return {
        "summary_report": result["summary_report"],
        "parsed_summary": result["parsed_summary"],
        "detailed_analysis": result["detailed_analysis"]
    }


@app.post("/report/", summary="Generate a detailed report for top N candidates")
async def generate_report(file: UploadFile = File(None), n: int = 3):
    """
    Generate a detailed analysis report for the top N ranked resumes based on the latest JD.
    If a JD file is provided, it will be processed and used to rank resumes first.
    If no file is provided, it uses the previously processed JD.
    """
    global latest_jd_text, latest_resume_ids

    # If a file is provided, process it and update state
    if file:
        jd_file_location = os.path.join(APP_DIR, file.filename)
        try:
            # Save the JD file
            with open(jd_file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            # Process the saved file
            text = get_document_text(jd_file_location)
            result = jd.classify_jd(text)

            result_dict = result.dict()
            result_dict["jd_text"] = text

            # Calculate scores and get top N
            all_scores = calculate_resume_scores(result_dict)
            top_n_ids = list(all_scores.keys())

            # Update global state
            latest_jd_text = text
            latest_resume_ids = top_n_ids

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing JD file: {str(e)}")
        finally:
            # Clean up the uploaded JD file
            if os.path.exists(jd_file_location):
                os.remove(jd_file_location)
    
    # If no file provided, check if we have state
    elif not latest_jd_text or not latest_resume_ids:
        raise HTTPException(
            status_code=400,
            detail="No JD provided and no previous JD processed. Please upload a JD file.",
        )

    # Ensure n is not greater than the number of available IDs
    ids_to_query = latest_resume_ids[:n]

    default_query = "Generate a detailed analysis of the top candidates based on the provided job description."
    
    # Define a directory to store the final reports
    reports_dir = os.path.join(APP_DIR, "final_reports")
    
    # Use the logic from llm.py to generate and save the report
    result, file_path = generate_and_save_report(default_query, latest_jd_text, ids_to_query, reports_dir)
        
    return {
        "summary_report": result["summary_report"],
        "parsed_summary": result["parsed_summary"],
        "detailed_analysis": result["detailed_analysis"],
        "report_path": file_path
    }


@app.get("/view-resume/{file_name}", summary="View a specific resume file")
def view_resume(file_name: str):
    """
    Searches for a resume by name in the 'cv' and 'uploaded_cvs' directories
    and returns it for viewing as a file response.
    """
    # Define allowed search directories
    search_dirs = [
        os.path.abspath(os.path.join(APP_DIR, "..", "cv")),
        os.path.abspath(UPLOAD_DIR),
    ]

    found_path = None
    for dir_path in search_dirs:
        # Use glob to find the file recursively
        search_pattern = os.path.join(dir_path, "**", file_name)
        file_paths = glob.glob(search_pattern, recursive=True)
        if file_paths:
            found_path = file_paths[0]
            break

    if not found_path:
        raise HTTPException(
            status_code=404, detail=f"Resume file '{file_name}' not found."
        )

    # Determine media type and content disposition
    media_type = "application/octet-stream"
    content_disposition_type = "attachment"
    if file_name.lower().endswith(".pdf"):
        media_type = "application/pdf"
        content_disposition_type = "inline"
    elif file_name.lower().endswith(".docx"):
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    return FileResponse(
        found_path,
        media_type=media_type,
        filename=file_name,
        content_disposition_type=content_disposition_type,
    )


@app.get("/preview-resume/{resume_id}", summary="Get resume content and file URL")
async def preview_resume(request: Request, resume_id: str):
    """
    Endpoint to get a resume's text content and a URL to the file.
    """
    try:
        # Retrieve the resume payload from Qdrant
        retrieved_points = config.QDRANT_CLIENT.retrieve(
            collection_name=config.CV_COLLECTION, ids=[resume_id], with_payload=True
        )

        if not retrieved_points:
            raise HTTPException(status_code=44, detail="Resume not found")

        payload = retrieved_points[0].payload
        file_path = payload.get("file_path")

        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Resume file not found on disk")

        # Get file content
        text_content = payload.get("page_content") or get_document_text(file_path)

        # Construct a URL using the /view-resume endpoint
        file_name = os.path.basename(file_path)
        file_url = request.url_for("view_resume", file_name=file_name)

        return {
            "resume_id": resume_id,
            "content": text_content,
            "file_url": str(file_url),
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# This catch-all route is now redundant if preview_resume provides a better URL.
# However, if other parts of the system rely on it, it can be kept.
# For now, I will comment it out in favor of the more specific /view-resume endpoint.
# @app.get("/{filepath:path}")
# async def get_file(filepath: str):
#     # ... (implementation)

# --------------------------------------------------------------------------
# Main execution
# --------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, port=8000, host="localhost")
