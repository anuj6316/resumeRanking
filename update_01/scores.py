from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from langchain_huggingface import HuggingFaceEmbeddings
import pandas as pd

client = QdrantClient(url="http://localhost:6333")
model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
RESUME_COLLECTION_NAME = "resumes_parse"

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

    # Get all resumes from Qdrant with their embeddings
    resumes, _ = client.scroll(
        collection_name=RESUME_COLLECTION_NAME, 
        with_payload=True, 
        with_vectors=True,
        limit=10000  # Adjust based on your collection size
    )
    
    results = {}
    
    for point in resumes:
        resume_id = point.payload.get("id")
        resume_text = point.payload.get("resume_text", "")
        
        # Get the full resume embedding vector from Qdrant
        resume_vec = np.array(point.vector, dtype=np.float32)
        
        # Calculate similarity between JD sections and full resume embedding
        def calculate_similarity(jd_vec):
            """Calculate cosine similarity between JD section and resume"""
            if jd_vec is None:
                return 0.0
            try:
                if np.any(np.isnan(jd_vec)) or np.any(np.isnan(resume_vec)):
                    return 0.0
                # Reshape vectors for cosine_similarity (needs 2D arrays)
                similarity = cosine_similarity([jd_vec], [resume_vec])[0][0]
                return float(similarity)
            except Exception as e:
                print(f"Error calculating similarity for resume {resume_id}: {e}")
                return 0.0
        
        # Calculate section scores
        skills_score = calculate_similarity(skills_vec)
        role_score = calculate_similarity(role_vec)
        education_score = calculate_similarity(education_vec) if education_vec is not None else 0.0
        certification_score = calculate_similarity(cert_vec) if cert_vec is not None else 0.0
        overall_semantic_score = calculate_similarity(jd_vec) if jd_vec is not None else 0.0

        # Experience score: numeric comparison
        jd_exp = jd_dict.get("experience", 0.0)
        resume_exp = point.payload.get("experience", 0.0)
        
        # Experience scoring logic
        if jd_exp:
            # If JD requires 0 experience (fresher), give full score if candidate is also fresher
            experience_score = 1.0 if resume_exp >= jd_exp  else 0.0
        else:
            # Score based on how close resume experience is to JD requirement
            if resume_exp >= jd_exp:
                experience_score = 1.0
            else:
                # Overqualified: slightly reduced score
                experience_score = 0.0
        
        # Combined education and certification score
        edu_cert_score = (education_score + certification_score) / 2.0
        
        # Store all scores for this resume
        results[resume_id] = {
            "skills_score": round(skills_score, 4),
            "role_score": round(role_score, 4),
            "experience_score": round(experience_score, 4),
            "education_score": round(education_score, 4),
            "certification_score": round(certification_score, 4),
            "edu_cert_score": round(edu_cert_score, 4),
            "overall_semantic_score": round(overall_semantic_score, 4),
        }
    
    # Sort by overall score (you can customize the weighting)
    sorted_results = calculate_overall_scores(results)
    
    return sorted_results


def calculate_overall_scores(results, weights=None):
    """
    Calculate overall score for each resume based on section scores.
    
    Args:
        results: Dictionary of resume scores
        weights: Dictionary of weights for each section. Default:
                 {'skills': 0.3, 'role': 0.25, 'experience': 0.25, 'edu_cert': 0.2}
    
    Returns:
        Dictionary sorted by overall_score in descending order
    """
    if weights is None:
        weights = {
            'skills_score': 30,
            'role_score': 20,
            'experience_score': 20,
            'edu_cert_score': 10,
            'overall_semantic_score': 20
        }
    
    for resume_id, scores in results.items():
        overall = (
            scores['skills_score'] * weights['skills_score'] +
            scores['role_score'] * weights['role_score'] +
            scores['experience_score'] * weights['experience_score'] +
            scores['edu_cert_score'] * weights['edu_cert_score'] +
            scores['overall_semantic_score'] * weights['overall_semantic_score']
        )
        scores['overall_score'] = round(overall, 4)
    
    # Sort by overall score
    sorted_results = dict(
        sorted(results.items(), key=lambda x: x[1]['overall_score'], reverse=True)
    )
    
    return sorted_results


def format_results_as_dataframe(results):
    """Convert results dictionary to a pandas DataFrame for better visualization"""
    df = pd.DataFrame.from_dict(results, orient='index')
    df.index.name = 'resume_id'
    df = df.reset_index()
    return df


def get_top_candidates(results, top_n=10):
    """Get top N candidates based on overall score"""
    sorted_items = sorted(results.items(), key=lambda x: x[1]['overall_score'], reverse=True)
    return dict(sorted_items[:top_n])


# Example usage function (for testing)
def main():
    # Example JD dictionary (your format)
    jd_dict = {
        "skills": [
            "Python", "Flask", "Django", "MySQL", "PostgreSQL", 
            "SQLite", "SQL", "APIs", "REST", "JSON", "Git", 
            "GitHub", "Selenium", "PyTest", "Pandas", "NumPy", 
            "Linux", "Unix", "Shell Scripting"
        ],
        "experience": 0.0,
        "role": "Python Developer",
        "education": [
            "Bachelor's degree in Computer Science",
            "Information Technology",
            "related field"
        ],
        "certification": [],
        "jd_text": "Full JD text here..."
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