import json
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from qdrant_client import QdrantClient
from config import Config
from dotenv import load_dotenv

# --- Load Environment and Configuration ---
load_dotenv()
config = Config()

# --- Import Prompt Templates ---
from scorer_prompt import template as scorer_template_str
from summary_prompt import template as summary_template_str


# --- Updated Pydantic Models for Enhanced Output ---
class EvidenceItem(BaseModel):
    skill: str = Field(description="The specific skill being evaluated")
    evidence_found: Optional[str] = Field(description="Exact text from resume that supports this skill")
    evidence_tier: str = Field(description="Tier of evidence: Exceptional, Strong, Moderate, Minimal, None")
    equivalency_considered: Optional[str] = Field(description="Any equivalent technology considered")
    confidence_level: str = Field(description="Confidence in assessment: High, Medium, Low")


class SectionAnalysis(BaseModel):
    score: int = Field(description="The score for this section (0-30 for Experience, 0-25 for others)")
    explanation: str = Field(description="Detailed explanation for the score")
    evidence_items: Optional[List[EvidenceItem]] = Field(description="List of specific evidence items that supported the score")


class Analysis(BaseModel):
    skills: SectionAnalysis
    experience: SectionAnalysis
    projects: SectionAnalysis
    certifications: SectionAnalysis
    formatting: SectionAnalysis


class ResumeScores(BaseModel):
    candidateName: str = Field(description="The name of the candidate.")
    overallScore: int = Field(description="The overall score for the resume (0-100).")
    analysis: Analysis
    summary: str = Field(description="A 2-3 sentence overview of the candidate.")
    jd_requirements: List[str] = Field(description="List of skills/requirements from the job description that were evaluated")
    total_possible_points: int = Field(description="Total points available for scoring")


# --- Initialize Qdrant Client ---
qdrant_client = QdrantClient(url="http://localhost:6333")


# --- Helper Functions ---
def get_resume_texts_from_ids(qdrant_client, collection_name, filter_resume_ids):
    """
    Retrieves the page content for a list of resume IDs from Qdrant.
    """
    if not filter_resume_ids:
        return []

    retrieved_points = qdrant_client.retrieve(
        collection_name=collection_name, ids=filter_resume_ids, with_payload=True
    )

    return [point.payload.get("page_content", "") for point in retrieved_points]


# --- Main Orchestration Function ---
def ai_res(query, jd, filter_resume_ids):
    """
    Orchestrates the two-phase process of scoring resumes and generating a summary.
    """
    print(
        f"Starting resume analysis for {len(filter_resume_ids)} resumes based on the JD."
    )

    # --- Phase 1: Score each resume individually against the JD ---
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    parser = PydanticOutputParser(pydantic_object=ResumeScores)

    # The scorer_prompt template contains a malformed JSON example which causes a
    # validation error when creating the PromptTemplate. The following code
    # removes this problematic section from the template string before it's used.
    start_marker = "The output must be a valid JSON object with the following structure:"
    end_marker = "RESUME TEXT TO ANALYZE:"
    start_index = scorer_template_str.find(start_marker)
    end_index = scorer_template_str.find(end_marker)

    template_for_prompt = scorer_template_str
    if start_index != -1 and end_index != -1:
        template_for_prompt = (
            scorer_template_str[:start_index] + scorer_template_str[end_index:]
        )

    scorer_prompt = PromptTemplate(
        template=template_for_prompt,
        input_variables=["resume_text", "jd"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    scorer_chain = scorer_prompt | llm | parser

    resume_texts = get_resume_texts_from_ids(
        qdrant_client, config.CV_COLLECTION, filter_resume_ids
    )

    scored_resumes = []
    for i, resume_text in enumerate(resume_texts):
        if not resume_text.strip():
            print(f"Skipping empty resume text for ID: {filter_resume_ids[i]}")
            continue
        try:
            print(f"Scoring resume {i + 1}/{len(resume_texts)}...")
            score = scorer_chain.invoke({"resume_text": resume_text, "jd": jd})
            scored_resumes.append(score.dict())
        except Exception as e:
            print(f"Error scoring resume {filter_resume_ids[i]}: {e}")
            # Add error handling with fallback
            error_resume = {
                "candidateName": f"Error Processing Resume {filter_resume_ids[i]}",
                "overallScore": 0,
                "analysis": {
                    "skills": {"score": 0, "explanation": "Processing error", "evidence_items": []},
                    "experience": {"score": 0, "explanation": "Processing error", "evidence_items": []},
                    "projects": {"score": 0, "explanation": "Processing error", "evidence_items": []},
                    "certifications": {"score": 0, "explanation": "Processing error", "evidence_items": []},
                    "formatting": {"score": 0, "explanation": "Processing error", "evidence_items": []}
                },
                "summary": "Error processing this resume",
                "jd_requirements": [],
                "total_possible_points": 100
            }
            scored_resumes.append(error_resume)

    if not scored_resumes:
        return "Could not score any of the provided resumes."

    # --- Phase 2: Generate a final summary report ---
    print("Generating final summary report...")
    summary_prompt = PromptTemplate(
        template=summary_template_str, input_variables=["json_objects"]
    )

    summary_chain = summary_prompt | llm | StrOutputParser()

    final_report = summary_chain.invoke({"json_objects": json.dumps(scored_resumes)})

    print("Analysis complete.")
    return final_report


# --- Example Usage ---
def main():
    filter_resume_ids = [
        "d9ccec00-128f-feb8-5609-eef9baa4ccde",
        "c902d79d-3d54-59db-bf0c-932b1e039aa1",
        "7d75f152-da0f-1148-1380-d5269b7e9aa6",
    ]
    jd = "Job Description: Frontend Developer with 5+ years of experience in React and cloud technologies."
    query = "Find the best frontend developer."

    response = ai_res(query, jd, filter_resume_ids)

    print("\n--- FINAL REPORT ---")
    print(response)


if __name__ == "__main__":
    main()
