from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader, DirectoryLoader
import os
from typing import List
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
import re
import total_exp_years as exp_years
import datetime
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

load_dotenv()
import logging

# Configurable section keywords
SECTION_KEYWORDS = {
    "education": ["education", "academic"],
    "skills": ["skills", "skillset"],
    "projects": ["projects", "project"],
    "certifications": ["certifications", "certificate"],
    "experience": ["experience", "experiences"],
    "work_experience": ["work experience", "professional experience", "employment history", "job history"]
}

def normalize_list(items):
    """Lowercase, strip, and deduplicate a list of strings."""
    return list(set([i.lower().strip() for i in items if i.strip()]))

def extract_section(raw_text, section):
    """Generic section extractor using config keywords."""
    cv_list = raw_text.split("\n")
    section_lines = []
    in_section = False
    for line in cv_list:
        if not in_section and any(kw in line.lower() for kw in SECTION_KEYWORDS[section]):
            in_section = True
            section_lines.append(line)
            continue
        if in_section and any(
            kw in line.lower() for kw in sum(SECTION_KEYWORDS.values(), []) if kw not in SECTION_KEYWORDS[section]
        ):
            break
        if in_section:
            section_lines.append(line)
    return "\n".join(section_lines)

# Section extractors
def extract_edu(raw_text):
    return extract_section(raw_text, "education")

def extract_skills(raw_text):
    return extract_section(raw_text, "skills")

def extract_projects(raw_text):
    return extract_section(raw_text, "projects")

def extract_certifications(raw_text):
    return extract_section(raw_text, "certifications")

def extract_experience(raw_text):
    return extract_section(raw_text, "experience")

def get_work_experience(raw_text):
    return extract_section(raw_text, "work_experience")

def load_docs():
    loader_pdf = DirectoryLoader(
        path="../knowledge_base/Resumes",
        glob="**/*.pdf",
        loader_cls=PyMuPDFLoader,
        show_progress=True,
    )
    docs = loader_pdf.load()
    loader_docx = DirectoryLoader(
        path="../knowledge_base/Resumes",
        glob="**/*.docx",
        loader_cls=Docx2txtLoader,
        show_progress=True,
    )
    docs.extend(loader_docx.load())
    return docs

# extrating the Education section from resumes

def exp_based_on_title(exp_section):
    pass

def main():
    docs = load_docs()
    for raw_text in docs:
        # extracted_education_section = extract_edu(raw_text.page_content)
        # print(extracted_education_section)
        # extracted_skill_section = extract_skills(raw_text.page_content)
        # print(extracted_skill_section)
        # extracted_project_section = extract_projects(raw_text.page_content)
        # print(extracted_project_section)
        # extracted_certification_section = extract_certifications(raw_text.page_content)
        # print(extracted_certification_section)
        print(raw_text.metadata['source'])
        work_exp_section = get_work_experience(raw_text.page_content)
        exp_section = extract_experience(raw_text.page_content)
        complete_exp = work_exp_section + '\n\n' + exp_section
        # Deduplicate lines in complete_exp
        unique_exp_section = exp_years.get_unique_experience(complete_exp)

        print(unique_exp_section)
        print("*"*50)

if __name__ == "__main__":
    main()