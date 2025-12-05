import json
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from qdrant_client import QdrantClient
from core.config import Config
from dotenv import load_dotenv

# --- Load Environment and Configuration ---
load_dotenv()
config = Config()

# --- Import Prompt Templates ---
from .scorer_prompt import template as scorer_template_str
from .summary_prompt import template as summary_template_str


# --- Updated Pydantic Models for Enhanced Output ---
# --- Updated Pydantic Models for Enhanced Output ---
class SkillsCompetency(BaseModel):
    score: int = Field(description="Score out of 30")
    max_score: int = Field(description="Max score for this section")
    reasoning: str = Field(description="Reasoning for the score")
    key_evidence: List[str] = Field(description="List of key evidence quotes")
    missing_critical_skills: List[str] = Field(description="List of missing critical skills")

class ExperienceDepth(BaseModel):
    score: int = Field(description="Score out of 20")
    max_score: int = Field(description="Max score for this section")
    reasoning: str = Field(description="Reasoning for the score")
    quantifiable_wins: List[str] = Field(description="List of quantifiable wins")

class RoleTrajectory(BaseModel):
    score: int = Field(description="Score out of 20")
    max_score: int = Field(description="Max score for this section")
    reasoning: str = Field(description="Reasoning for the score")
    red_flags: List[str] = Field(description="List of red flags")

class EducationRequirements(BaseModel):
    score: int = Field(description="Score out of 10")
    max_score: int = Field(description="Max score for this section")
    reasoning: str = Field(description="Reasoning for the score")
    red_flags: Optional[List[str]] = Field(default=[], description="List of red flags")

class StrategicFit(BaseModel):
    score: int = Field(description="Score out of 20")
    max_score: int = Field(description="Max score for this section")
    reasoning: str = Field(description="Reasoning for the score")
    red_flags: Optional[List[str]] = Field(default=[], description="List of red flags")

class ScoringBreakdown(BaseModel):
    skills_competency: SkillsCompetency
    experience_depth: ExperienceDepth
    role_trajectory: RoleTrajectory
    education_requirements: EducationRequirements
    strategic_fit: StrategicFit

class FinalVerdict(BaseModel):
    decision: str = Field(description="Strong Hire | Hire | Conditional Hire | No Hire")
    main_argument: str = Field(description="Summary argument")
    hiring_manager_notes: str = Field(description="Interview questions or notes")

class ResumeScores(BaseModel):
    candidateName: str = Field(description="The name of the candidate.")
    overallScore: int = Field(description="The overall score for the resume (0-100).")
    scoring_breakdown: ScoringBreakdown
    final_verdict: FinalVerdict

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



def parse_summary_report(report_text: str) -> dict:
    """
    Parses the markdown summary report into distinct sections.
    """
    sections = {
        "table_of_contents": "",
        "executive_ranking": "",
        "deep_dive_analysis": ""
    }

    # Normalize newlines
    text = report_text.replace("\r\n", "\n")

    # Define regex patterns for sections
    # Using specific headers from the summary_prompt.py
    patterns = {
        "table_of_contents": r"(?i)## Table of Contents\s*(.*?)\s*(?=## Executive Ranking|$)",
        "executive_ranking": r"(?i)## Executive Ranking\s*(.*?)\s*(?=## Deep Dive Analysis|$)",
        "deep_dive_analysis": r"(?i)## Deep Dive Analysis\s*(.*?)\s*$"
    }

    import re
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.DOTALL)
        if match:
            sections[key] = match.group(1).strip()
    
    return sections


# --- Main Orchestration Function ---
def ai_res(query, jd, filter_resume_ids):
    """
    Orchestrates the two-phase process of scoring resumes and generating a summary.
    """
    print("https://33dd0bcbe6a3.ngrok-free.app/" +
        f"Starting resume analysis for {len(filter_resume_ids)} resumes based on the JD."
    )

    # --- Phase 1: Score each resume individually against the JD ---
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    parser = PydanticOutputParser(pydantic_object=ResumeScores)

    scorer_prompt = PromptTemplate(
        template=scorer_template_str,
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
            scored_resumes.append(score.model_dump())
        except Exception as e:
            print(f"Error scoring resume {filter_resume_ids[i]}: {e}")
            # Add error handling with fallback
            error_resume = {
                "candidateName": f"Error Processing Resume {filter_resume_ids[i]}",
                "overallScore": 0,
                "scoring_breakdown": {
                    "skills_competency": {"score": 0, "max_score": 30, "reasoning": "Processing error", "key_evidence": [], "missing_critical_skills": []},
                    "experience_depth": {"score": 0, "max_score": 20, "reasoning": "Processing error", "quantifiable_wins": []},
                    "role_trajectory": {"score": 0, "max_score": 20, "reasoning": "Processing error", "red_flags": []},
                    "education_requirements": {"score": 0, "max_score": 10, "reasoning": "Processing error", "red_flags": []},
                    "strategic_fit": {"score": 0, "max_score": 20, "reasoning": "Processing error", "red_flags": []}
                },
                "final_verdict": {
                    "decision": "No Hire",
                    "main_argument": "Error processing this resume",
                    "hiring_manager_notes": "No data available due to processing error."
                }
            }
            scored_resumes.append(error_resume)

    if not scored_resumes:
        return "Could not score any of the provided resumes."

    print("Scoring complete.\n\n")
    for i, resume in enumerate(scored_resumes):
        print(f"Resume {i + 1}/{len(scored_resumes)}:")
        print(f"Candidate Name: {resume['candidateName']}")
        print(f"Overall Score: {resume}")
        print("\n")
    # --- Phase 2: Generate a final summary report ---
    print("Generating final summary report...")
    summary_prompt = PromptTemplate(
        template=summary_template_str, input_variables=["json_objects"]
    )

    summary_chain = summary_prompt | llm | StrOutputParser()

    final_report = summary_chain.invoke({"json_objects": json.dumps(scored_resumes)})

    # Clean up markdown code blocks if present
    final_report = final_report.replace("```markdown", "").replace("```", "").strip()

    # Parse the report into sections
    parsed_summary = parse_summary_report(final_report)

    print("Analysis complete.")
    return {
        "detailed_analysis": scored_resumes,
        "summary_report": final_report,
        "parsed_summary": parsed_summary
    }


def generate_and_save_report(query, jd, filter_resume_ids, output_dir):
    """
    Generates the report using ai_res and saves it to the specified directory.
    Returns the content and the file path.
    """
    import os
    from datetime import datetime

    result = ai_res(query, jd, filter_resume_ids)
    report_content = result["summary_report"]

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.join(output_dir, f"resume_analysis_report_{timestamp}.md")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Successfully saved report to {file_path}")
    except Exception as e:
        print(f"Error saving report: {e}")
        # Even if saving fails, return the content
    
    return result, file_path


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
    print(response['summary_report'])


if __name__ == "__main__":
    main()
