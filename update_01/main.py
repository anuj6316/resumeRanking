from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
import os
from typing import List
from resume_db import upload_cv

app = FastAPI()

# upload multiple pdf or docx files to the qdrant database
@app.post('/upload-cv/')
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

if __name__ == "__main__":
    uvicorn.run(
        app,
        port=8000,
        host='localhost',
        reload=True
    )