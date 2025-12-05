# Resume Ranking System

A powerful AI-powered tool to rank resumes against a job description using RAG (Retrieval-Augmented Generation) and LLMs.

## Features

- **Resume Upload**: Upload multiple resumes (PDF/DOCX).
- **Job Description Analysis**: Analyze JDs to extract key skills and requirements.
- **Intelligent Scoring**: Rank candidates based on:
    - Keyword Matching
    - Semantic Similarity (Vector Search)
    - Experience & Role Alignment
- **LLM-Powered Insights**: Chat with the resumes to get detailed summaries and comparisons.
- **Interactive UI**: User-friendly interface built with Gradio.

## Prerequisites

Before running the project, ensure you have the following installed:

- **Python 3.10+**
- **Docker** & **Docker Compose** (for the Qdrant vector database)
- **Git**

## Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd resumeRanking
```

### 2. Set up the Environment

It is recommended to use a virtual environment to manage dependencies.

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note**: If you encounter an error regarding `spacy`, run the following command to download the required model:
> ```bash
> python -m spacy download en_core_web_sm
> ```

### 4. Configuration

Create a `.env` file in the root directory and add your Google API Key (required for the LLM).

```bash
# .env file
GOOGLE_API_KEY=your_google_api_key_here
```

### 5. Start the Vector Database (Qdrant)

The system uses Qdrant to store and search resume embeddings. Run it using Docker:

```bash
docker-compose up -d
```
*This starts Qdrant on `localhost:6333`.*

## Running the Application

You need to run both the backend API and the frontend UI.

### 1. Start the Backend API

Open a terminal and run:

```bash
# Ensure venv is activated
python main.py
```
*The backend will start at `http://localhost:8000`.*

### 2. Start the Frontend UI

Open a **new terminal**, activate the virtual environment, and run:

```bash
source venv/bin/activate
python ui/new_gradio_ui.py
```
*The UI will launch at `http://127.0.0.1:7860`.*

## Usage Guide

1.  **Open the UI**: Go to `http://127.0.0.1:7860` in your browser.
2.  **Upload Resumes**:
    - Go to the **"Step 1: Upload Resumes"** tab.
    - Select and upload your candidate resumes (PDFs).
3.  **Score Candidates**:
    - Go to the **"Step 2: Score Resumes"** tab.
    - Upload a Job Description file.
    - Click **"Get Resume Scores"**.
    - The system will display a ranked list of candidates with detailed scores.
4.  **Chat with Data**:
    - Go to the **"Step 3: Chat with Resumes"** tab.
    - Ask questions like "Who is the best candidate for a Python role?" or "Summarize the experience of Gina Jones."

## Troubleshooting

- **Port Conflicts**:
    - If port `6333` is busy, check if another Qdrant instance is running.
    - If port `8000` is busy, ensure the backend isn't already running (`lsof -i :8000`).
- **Connection Errors**:
    - Ensure Qdrant is running (`docker ps`).
    - Ensure the Backend is running before using the Frontend.
- **Missing Models**:
    - The first run might take a few minutes to download embedding models. Check the backend console for progress.

## Project Structure

- `main.py`: FastAPI backend entry point.
- `core/`: Configuration settings (`config.py`).
- `database/`: Database interactions (`resume_db.py`).
- `services/`: Business logic.
    - `llm/`: LLM integration (`llm.py`, prompts).
    - `scoring/`: Scoring algorithms (`scores.py`).
    - `resume_handler.py`: Resume parsing logic.
- `ui/`: Frontend code (`new_gradio_ui.py`).
- `utils/`: Utility functions.
