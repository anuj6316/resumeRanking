from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from langchain_huggingface import HuggingFaceEmbeddings
import pandas as pd
from config import Config

config = Config()

model = config.EMBEDDING_FUNCTION
client = config.QDRANT_CLIENT


def calculate_resume_scores(jd_dict):
    """
    Calculate section-wise similarity scores between a JD and all resumes in Qdrant.

    Args:
        jd_dict: Dictionary containing JD sections with keys:
                 - skills: List[str]
                 - role: str
                 - experience: float
                 - education: List[str]
                 - certification: List[str]
                 - jd_text: str (full JD text)

    Returns:
        Dictionary of scores keyed by resume_id with section scores
    """

    # Prepare section texts for embedding by joining lists
    skills_text = " ".join(jd_dict.get("skills", []))
    role_text = jd_dict.get("role", "")
    education_text = " ".join(jd_dict.get("education", []))
    cert_text = " ".join(jd_dict.get("certification", []))
    jd_text = " ".join(jd_dict.get("jd_text", ""))

    # Embed JD sections
    def safe_embed(text):
        """Safely embed text, returning None if text is empty or embedding fails"""
        if not text or not text.strip():
            return None
        try:
            vec = model.embed_query(text)
            if vec is None or np.any(np.isnan(vec)):
                return None
            return np.array(vec, dtype=np.float32)
        except Exception as e:
            print(f"Error embedding text: {e}")
            return None

    skills_vec = safe_embed(skills_text)
    role_vec = safe_embed(role_text)
    education_vec = safe_embed(education_text)
    cert_vec = safe_embed(cert_text)
    jd_vec = safe_embed(jd_text)

    # Search for similar resumes in Qdrant
    limit = 20  # Number of results to return for each search

    def search_qdrant(vector):
        if vector is None:
            return []
        return client.query_points(
            collection_name=config.CV_COLLECTION,
            query=vector.tolist(),  # Convert numpy array to list
            limit=limit,
            with_payload=True,
        ).points

    skills_results = search_qdrant(skills_vec)
    role_results = search_qdrant(role_vec)
    education_results = search_qdrant(education_vec)
    cert_results = search_qdrant(cert_vec)
    overall_results = search_qdrant(jd_vec)

    # Combine the results
    results = {}
    all_results = {
        "semantic_skills_score": skills_results,
        "role_score": role_results,
        "education_score": education_results,
        "certification_score": cert_results,
        "overall_semantic_score": overall_results,
    }

    for section, search_results in all_results.items():
        for point in search_results:
            resume_id = point.id
            if resume_id not in results:
                results[resume_id] = {
                    "person_name": point.payload.get("person_name", "Unknown"),
                    "file_path": point.payload.get("file_path", "Unknown"),
                    "keyword_skills_score": 0,
                    "semantic_skills_score": 0,
                    "role_score": 0,
                    "experience_score": 0,
                    "education_score": 0,
                    "certification_score": 0,
                    "edu_cert_score": 0,
                    "overall_semantic_score": 0,
                }
            results[resume_id][section] = round(point.score, 4)

    # Experience score: numeric comparison and skill score: word matching
    for resume_id, scores in results.items():
        # Retrieve the resume payload to get the total experience
        retrieved_points = client.retrieve(
            collection_name=config.CV_COLLECTION, ids=[resume_id], with_payload=True
        )
        if not retrieved_points:
            continue

        # Keyword-based skills score
        jd_skills = jd_dict.get("skills", [])
        if jd_skills:
            resume_text = retrieved_points[0].payload.get("page_content", "").lower()
            matched_count = sum(
                1 for skill in jd_skills if skill.lower() in resume_text
            )
            skills_score = matched_count / len(jd_skills)
        else:
            skills_score = 0.0
        results[resume_id]["keyword_skills_score"] = skills_score

        resume_exp = retrieved_points[0].payload.get("total_exp", 0.0)
        jd_exp = jd_dict.get("experience", 0.0)

        if jd_exp:
            experience_score = 1.0 if resume_exp >= jd_exp else 0.0
        else:
            if resume_exp >= jd_exp:
                experience_score = 1.0
            else:
                experience_score = 0.0
        results[resume_id]["experience_score"] = experience_score
        results[resume_id]["edu_cert_score"] = (
            results[resume_id]["education_score"]
            + results[resume_id]["certification_score"]
        ) / 2.0

    # Sort by overall score (you can customize the weighting)
    sorted_results = calculate_overall_scores(results)

    return sorted_results


def calculate_overall_scores(results, weights=None):
    """
    Calculate overall score for each resume based on section scores.

    Args:
        results: Dictionary of resume scores
        weights: Dictionary of weights for each section.

    Returns:
        Dictionary sorted by overall_score in descending order
    """
    if weights is None:
        weights = {
            "keyword_skills_score": 15,
            "semantic_skills_score": 15,
            "role_score": 20,
            "experience_score": 20,
            "edu_cert_score": 10,
            "overall_semantic_score": 20,
        }

    for resume_id, scores in results.items():
        overall = (
            scores["keyword_skills_score"] * weights["keyword_skills_score"]
            + scores["semantic_skills_score"] * weights["semantic_skills_score"]
            + scores["role_score"] * weights["role_score"]
            + scores["experience_score"] * weights["experience_score"]
            + scores["edu_cert_score"] * weights["edu_cert_score"]
            + scores["overall_semantic_score"] * weights["overall_semantic_score"]
        )
        scores["overall_score"] = round(overall, 4)

    # Sort by overall score
    sorted_results = dict(
        sorted(results.items(), key=lambda x: x[1]["overall_score"], reverse=True)
    )

    return sorted_results


def format_results_as_dataframe(results):
    """Convert results dictionary to a pandas DataFrame for better visualization"""
    df = pd.DataFrame.from_dict(results, orient="index")
    df.index.name = "resume_id"
    df = df.reset_index()
    return df


def get_top_candidates(results, top_n=10):
    """Get top N candidates based on overall score"""
    sorted_items = sorted(
        results.items(), key=lambda x: x[1]["overall_score"], reverse=True
    )
    return dict(sorted_items[:top_n])


# Example usage function (for testing)
def main():
    # Example JD dictionary (your format)
    jd_dict = {
        "skills": [
            "Python",
            "Flask",
            "Django",
            "MySQL",
            "PostgreSQL",
            "SQLite",
            "SQL",
            "APIs",
            "REST",
            "JSON",
            "Git",
            "GitHub",
            "Selenium",
            "PyTest",
            "Pandas",
            "NumPy",
            "Linux",
            "Unix",
            "Shell Scripting",
        ],
        "experience": 0.0,
        "role": "Python Developer",
        "education": [
            "Bachelor's degree in Computer Science",
            "Information Technology",
            "related field",
        ],
        "certification": [],
        "jd_text": "Full JD text here...",
    }

    # Calculate scores
    results = calculate_resume_scores(jd_dict)

    # Display results
    print("\n=== Top 10 Candidates ===")
    top_candidates = get_top_candidates(results, top_n=100)

    for resume_id, scores in top_candidates.items():
        print(f"\nResume ID: {resume_id}")
        print(f"  Overall Score: {scores['overall_score']}")
        print(f"  Skills Score: {scores['skills_score']}")
        print(f"  Role Score: {scores['role_score']}")
        print(f"  Experience Score: {scores['experience_score']}")
        print(f"  Education Score: {scores['education_score']}")
        print(f"  Certification Score: {scores['certification_score']}")
        print(f"  Edu+Cert Score: {scores['edu_cert_score']}")
        print(f"  Semantic Score: {scores['overall_semantic_score']}")

    # Or display as DataFrame
    df = format_results_as_dataframe(results)
    print("\n=== Results as DataFrame ===")
    print(df)

    return results


if __name__ == "__main__":
    main()
