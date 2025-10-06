import pandas as pd
import json
import tiktoken
import os
from qdrant_client import QdrantClient

# --- Configuration ---
# Get the absolute path of the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# You can change these values to estimate the cost for different scenarios.
NUM_RESUMES = 10
MODEL_NAME = "o4-mini"

# Qdrant Configuration
QDRANT_URL = "http://localhost:6333"
CV_COLLECTION_NAME = "cv_embeddings"

# Pricing for gpt-4o (as of late 2024).
# Prices are per 1 Million tokens.
# Please check the official OpenAI pricing page for the latest rates.
PRICE_PER_1M_INPUT_TOKENS = 1.10
PRICE_PER_1M_OUTPUT_TOKENS = 4.40

# --- Helper Functions ---


def load_prompt_template(file_path):
    """Loads a prompt template from a file."""
    try:
        with open(file_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: Prompt file not found at {file_path}")
        return ""


def generate_fake_scorer_output():
    """Generates a fake JSON output for Phase 1 to simulate the LLM's response."""
    return {
        "candidateName": "John Doe",
        "overallScore": 85,
        "analysis": {
            "skills": {"score": 25, "explanation": "Excellent match."},
            "experience": {"score": 20, "explanation": "Very relevant."},
            "projects": {"score": 15, "explanation": "Good projects."},
            "certifications": {"score": 5, "explanation": "Relevant certs."},
            "formatting": {"score": 10, "explanation": "Clean format."},
        },
        "summary": "A strong candidate with relevant skills and experience.",
    }


def generate_fake_summary_output(num_resumes):
    """Generates a fake Markdown report for Phase 2."""
    header = "## Candidate Summary Report\n\n"
    candidate_section = "### John Doe\n- **Overall Score:** 85/100\n- **Summary:** A strong candidate.\n"
    return header + (candidate_section * num_resumes)


def count_tokens(text, encoding):
    """Counts the number of tokens in a string using tiktoken."""
    return len(encoding.encode(text))


# --- Main Calculation Logic ---
def calculate_price():
    """Calculates the estimated price and returns a pandas DataFrame."""

    # Get the encoding for the model
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        print(f"Error getting tiktoken encoding: {e}")
        print("Please make sure 'tiktoken' is installed (`pip install tiktoken`).")
        return None

    # 1. Load prompts using absolute paths
    scorer_prompt = load_prompt_template(os.path.join(SCRIPT_DIR, "scorer_prompt.py"))
    summary_prompt = load_prompt_template(os.path.join(SCRIPT_DIR, "summary_prompt.py"))

    # 2. Fetch real resumes from Qdrant
    try:
        qdrant_client = QdrantClient(url=QDRANT_URL)
        points, _ = qdrant_client.scroll(
            collection_name=CV_COLLECTION_NAME, limit=NUM_RESUMES, with_payload=True
        )
        resume_texts = [point.payload.get("page_content", "") for point in points]
        if len(resume_texts) < NUM_RESUMES:
            print(
                f"Warning: Could only fetch {len(resume_texts)} resumes from the database. The estimate will be based on this number."
            )
        actual_num_resumes = len(resume_texts)
        if actual_num_resumes == 0:
            print("Error: No resumes found in the Qdrant database.")
            return None
    except Exception as e:
        print(f"Error connecting to Qdrant or fetching resumes: {e}")
        print(
            "Please ensure Qdrant is running and the collection '{CV_COLLECTION_NAME}' exists."
        )
        return None

    # --- Phase 1: Scoring Calculation ---
    total_phase1_input_tokens = 0
    for resume_text in resume_texts:
        total_phase1_input_tokens += count_tokens(scorer_prompt + resume_text, encoding)

    fake_scorer_json = generate_fake_scorer_output()
    phase1_output_tokens_per_resume = count_tokens(
        json.dumps(fake_scorer_json), encoding
    )
    total_phase1_output_tokens = phase1_output_tokens_per_resume * actual_num_resumes

    phase1_input_cost = (
        total_phase1_input_tokens / 1_000_000
    ) * PRICE_PER_1M_INPUT_TOKENS
    phase1_output_cost = (
        total_phase1_output_tokens / 1_000_000
    ) * PRICE_PER_1M_OUTPUT_TOKENS
    total_phase1_cost = phase1_input_cost + phase1_output_cost

    # --- Phase 2: Summarization Calculation ---
    all_scorer_jsons = [
        generate_fake_scorer_output() for _ in range(actual_num_resumes)
    ]
    phase2_input_tokens = count_tokens(
        summary_prompt + json.dumps(all_scorer_jsons), encoding
    )

    fake_summary = generate_fake_summary_output(actual_num_resumes)
    phase2_output_tokens = count_tokens(fake_summary, encoding)

    phase2_input_cost = (phase2_input_tokens / 1_000_000) * PRICE_PER_1M_INPUT_TOKENS
    phase2_output_cost = (phase2_output_tokens / 1_000_000) * PRICE_PER_1M_OUTPUT_TOKENS
    total_phase2_cost = phase2_input_cost + phase2_output_cost

    # --- Create DataFrame ---
    total_cost = total_phase1_cost + total_phase2_cost

    data = {
        "Phase": ["Phase 1: Scoring", "Phase 2: Summarization", "Total"],
        "Description": [
            f"{actual_num_resumes} resumes, 1 LLM call per resume",
            "1 LLM call for the final report",
            "Total estimated cost",
        ],
        "Input Tokens": [total_phase1_input_tokens, phase2_input_tokens, "-"],
        "Output Tokens": [total_phase1_output_tokens, phase2_output_tokens, "-"],
        "Estimated Cost (USD)": [total_phase1_cost, total_phase2_cost, total_cost],
    }
    df = pd.DataFrame(data)
    df["Estimated Cost (USD)"] = df["Estimated Cost (USD)"].round(6)

    return df


if __name__ == "__main__":
    print(
        f"Calculating estimated cost for up to {NUM_RESUMES} resumes from Qdrant using {MODEL_NAME}...\n"
    )
    price_df = calculate_price()
    if price_df is not None:
        print(price_df.to_string())
        print(
            "\nDisclaimer: This is an estimate. Actual costs may vary based on resume length, model, and pricing."
        )
