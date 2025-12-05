# System Architecture

## Overview
The Resume Ranking System is a modular application designed to automate the screening of candidates by analyzing resumes against job descriptions. It leverages **RAG (Retrieval-Augmented Generation)** to provide semantic search capabilities and **LLMs (Large Language Models)** for intelligent reasoning and summarization.

## Technology Stack

- **Backend**: FastAPI (Python)
- **Vector Database**: Qdrant (Dockerized)
- **LLM Integration**: LangChain + Google Gemini (via `langchain-google-genai`)
- **Embeddings**: HuggingFace (`sentence-transformers/all-mpnet-base-v2`, `all-MiniLM-L6-v2`)
- **Frontend**: Gradio
- **Document Processing**: PyMuPDF, Docx2txt, SpaCy

## High-Level Data Flow

1.  **Ingestion (Upload)**
    - User uploads resumes (PDF/DOCX) via the UI.
    - `resume_handler.py` extracts text and metadata (skills, experience, etc.).
    - Text is chunked and embedded using HuggingFace models.
    - Vectors and payloads are stored in **Qdrant**.

2.  **Scoring (Retrieval & Ranking)**
    - User uploads a Job Description (JD).
    - JD is parsed and embedded.
    - System performs a hybrid search:
        - **Semantic Search**: Cosine similarity between JD vector and Resume vectors.
        - **Keyword Match**: Overlap of specific skills.
        - **Experience Check**: Numeric comparison of years of experience.
    - `scores.py` aggregates these metrics into a final weighted score.

3.  **Analysis (LLM Query)**
    - User asks a question about the top candidates.
    - `llm.py` retrieves the full text of the top N candidates.
    - A prompt is constructed with the User Query + Candidate Data + JD.
    - Google Gemini generates a natural language response (summary, comparison, or recommendation).

## Component Design

### 1. Core (`core/`)
- **`config.py`**: Centralized configuration management (environment variables, Qdrant client initialization, model selection).

### 2. Services (`services/`)
- **`resume_handler.py`**: Handles file reading and text extraction using specific loaders. Uses SpaCy for NER (Name Extraction).
- **`sections_extractor_and_storage.py`**: specialized logic for extracting structured sections (Education, Skills) from JDs.
- **`scoring/scores.py`**: Implements the ranking algorithm. It fetches vectors from Qdrant and calculates a composite score.
- **`llm/llm.py`**: Manages interactions with the Google Gemini API. Contains the logic for the "Chat with Data" feature.

### 3. Database (`database/`)
- **`resume_db.py`**: Wrapper functions for Qdrant operations (upload, upsert).

### 4. UI (`ui/`)
- **`new_gradio_ui.py`**: The main frontend entry point. Defines the layout (Tabs) and connects UI events to backend API calls.

## Directory Structure

```
resumeRanking/
├── core/               # Config and singletons
├── database/           # DB adapters
├── services/           # Business logic
│   ├── llm/            # AI/LLM logic
│   └── scoring/        # Ranking logic
├── ui/                 # Frontend code
├── utils/              # Helpers
├── knowledge_base/     # Local storage for files
└── main.py             # API Entry point
```
