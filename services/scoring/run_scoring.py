import os
import sys

# Ensure the current directory is in the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from sections_extractor_and_storage import classify_jd
from scores import calculate_resume_scores, get_top_candidates, format_results_as_dataframe

def main():
    # Sample Job Description
    jd_text = """
    Job Title: Python Developer
    Experience: 3+ years
    Skills: Python, Django, Flask, SQL, REST APIs, Docker, Git
    Role: Backend Developer
    Education: Bachelor's in Computer Science
    """
    
    print("Processing Job Description...")
    print(f"JD Text:\n{jd_text}\n")

    # 1. Classify JD to extract sections
    try:
        classified_jd = classify_jd(jd_text)
        jd_dict = classified_jd.dict()
        jd_dict["jd_text"] = jd_text
        print("JD Classified Successfully.")
        print(f"Extracted Skills: {jd_dict.get('skills')}")
    except Exception as e:
        print(f"Error classifying JD: {e}")
        return

    # 2. Calculate scores
    print("\nCalculating Scores...")
    try:
        results = calculate_resume_scores(jd_dict)
    except Exception as e:
        print(f"Error calculating scores: {e}")
        return

    # 3. Get Top 5 Candidates
    print("\n=== Top 5 Candidates ===")
    top_candidates = get_top_candidates(results, top_n=5)

    if not top_candidates:
        print("No candidates found.")
    else:
        for resume_id, scores in top_candidates.items():
            print(f"\nResume ID: {resume_id}")
            print(f"  Name: {scores.get('person_name', 'Unknown')}")
            print(f"  Overall Score: {scores['overall_score']}")
            print(f"  Skills Score: {scores.get('keyword_skills_score', 0)}")
            print(f"  Semantic Score: {scores.get('overall_semantic_score', 0)}")

    # Optional: Display as DataFrame
    # df = format_results_as_dataframe(top_candidates)
    # print("\n=== Results DataFrame ===")
    # print(df)

if __name__ == "__main__":
    main()
