# API Reference

Base URL: `http://localhost:8000`

## Endpoints

### 1. General

#### `GET /total-resumes/`
Returns the total count of resumes currently indexed in the database.

- **Response**:
  ```json
  {
    "total": 15
  }
  ```

### 2. Ingestion

#### `POST /upload-cv/`
Uploads one or more resume files to the system.

- **Body**: `multipart/form-data`
    - `files`: List of files (PDF or DOCX).
- **Response**:
  ```json
  {
    "results": [
      {
        "filename": "candidate1.pdf",
        "status": "success",
        "detail": "..."
      }
    ]
  }
  ```

### 3. Scoring

#### `POST /scores/`
Analyzes a Job Description and ranks existing resumes against it.

- **Query Parameters**:
    - `n`: (Optional) Number of top candidates to return (default: 5).
- **Body**: `multipart/form-data`
    - `file`: The Job Description file (PDF or DOCX).
- **Response**:
  A dictionary where keys are Resume IDs and values are score objects.
  ```json
  {
    "resume-uuid-1": {
      "overall_score": 0.85,
      "skills_score": 0.9,
      "experience_score": 1.0,
      ...
    },
    ...
  }
  ```

### 4. Analysis

#### `POST /report/`
Generates a detailed analysis report for the top N ranked resumes.

- **Query Parameters**:
    - `n`: (Optional) Number of top candidates to consider (default: 5).
- **Body**: `multipart/form-data` (Optional)
    - `file`: A Job Description file (PDF or DOCX).
    - *Note*: If `file` is provided, the system will first process the JD and rank resumes. If not provided, it uses the last processed JD.
- **Response**:
  ```json
  {
    "results": "Markdown content of the report...",
    "report_path": "/path/to/saved/report.md"
  }
  ```

#### `POST /query/`
Asks a natural language question about the top-ranked candidates. **Must be called after `/scores/`** as it relies on the context of the last processed JD.

- **Query Parameters**:
    - `n`: (Optional) Number of top candidates to consider (default: 5).
- **Body**: `application/json`
  ```json
  {
    "Query": "Who has the most React experience?"
  }
  ```
- **Response**:
  ```json
  {
    "results": "Based on the analysis, Candidate A has 5 years of React experience..."
  }
  ```

### 5. Retrieval

#### `GET /view-resume/{file_name}`
Downloads or views a specific resume file.

- **Path Parameters**:
    - `file_name`: The name of the file to retrieve.
- **Response**: File stream (PDF/DOCX).

#### `GET /preview-resume/{resume_id}`
Retrieves the text content and download URL for a specific resume ID.

- **Path Parameters**:
    - `resume_id`: The UUID of the resume in Qdrant.
- **Response**:
  ```json
  {
    "resume_id": "...",
    "content": "Full text content of the resume...",
    "file_url": "http://localhost:8000/view-resume/candidate1.pdf"
  }
  ```
