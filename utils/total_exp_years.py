def get_unique_experience(exp_text):
    exp_lines = exp_text.split('\n')
    seen = set()
    unique_exp_lines = []
    prev_line = None
    for line in exp_lines:
        line_stripped = line.strip()
        if line_stripped and (line_stripped not in seen) and (line_stripped != prev_line):
            unique_exp_lines.append(line_stripped)
            seen.add(line_stripped)
        prev_line = line_stripped
    return '\n'.join(unique_exp_lines)
from datetime import datetime

def calculate_total_experience(exp_month_years):
    # exp_month_years: list of strings like 'May 2021', '2021 May', etc.
    dates = []
    for item in exp_month_years:
        # Try month before year
        try:
            dt = datetime.strptime(item, "%b %Y")
        except ValueError:
            try:
                dt = datetime.strptime(item, "%B %Y")
            except ValueError:
                # Try year before month
                try:
                    dt = datetime.strptime(item, "%Y %b")
                except ValueError:
                    try:
                        dt = datetime.strptime(item, "%Y %B")
                    except ValueError:
                        continue
        dates.append(dt)
    # If odd, add current date (2025-09)
    if len(dates) % 2 == 1:
        dates = [datetime(2025, 9, 1)] + dates
    total_months = 0
    for i in range(0, len(dates), 2):
        start = dates[i]
        end = dates[i+1]
        diff = abs((start.year - end.year) * 12 + (start.month - end.month))
        total_months += diff
    total_years = round(total_months / 12, 2)
    return total_years, total_months

import re
def check_month_position(text):
    months = r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December"
    before_pattern = rf"({months})[\s\-]*\d{{4}}"
    # after_pattern = rf"\d{{4}}[\s\-]*({months})"
    before_matches = re.findall(before_pattern, text, re.IGNORECASE)
    # after_matches = re.findall(after_pattern, text, re.IGNORECASE)
    result = []
    # Store found patterns and their positions
    for match in re.finditer(before_pattern, text, re.IGNORECASE):
        result.append(match.group())
    # for match in re.finditer(after_pattern, text, re.IGNORECASE):
    #     result.append(match.group())
    return result
def extract_years(exp_str):
    years = re.findall(r'\d{4}', exp_str)
    # If odd, add 2025 at the beginning
    if len(years) % 2 == 1:
        years = ["2025"] + years
    ans = 0
    # Calculate total years (difference of pairs)
    for i in range(0, len(years), 2):
        start = int(years[i])
        end = int(years[i+1])
        ans += abs(start - end)
    return years, ans

def total_exp_yrs(unique_exp_section):
    exp_month_years = check_month_position(unique_exp_section)
    if exp_month_years:
        ## total_years, total_months
        ans, _ = calculate_total_experience(exp_month_years)
    else:
        _, ans = extract_years(unique_exp_section)
    return ans

def main():
    def clean_text(text):
        return text.replace("\n", " ").replace("  ", " ")
    
    from langchain_community.document_loaders import PyMuPDFLoader, DirectoryLoader, Docx2txtLoader
    import services.resume_handler as rh
    # loader = PyMuPDFLoader("/home/anujkumar/Desktop/resumeRanking/knowledge_base/Resumes/react-developer-resume-example.pdf")
    # pass
    loader = DirectoryLoader(
        path="/home/anujkumar/Desktop/resumeRanking/knowledge_base/Resumes/",
        glob="**/*.pdf",
        loader_cls=PyMuPDFLoader,
        recursive=True,
        show_progress=True
    )
    docs = loader.load()
    loader = DirectoryLoader(
        path="/home/anujkumar/Desktop/resumeRanking/knowledge_base/Resumes/",
        glob="**/*.docx",
        loader_cls=Docx2txtLoader,
        show_progress=True
    )
    docs.extend(loader.load())
    # print(docs[0].page_content)
    for i in docs:
        experience_text = rh.extract_experience(i.page_content)

        work_exp_section = rh.get_work_experience(i.page_content)
        exp_section = rh.extract_experience(i.page_content)
        complete_exp = work_exp_section + '\n\n' + exp_section
        unique_exp_section = get_unique_experience(complete_exp)
        exp_month_years = check_month_position(unique_exp_section)
        print(exp_month_years)
        if exp_month_years:
            print(calculate_total_experience(exp_month_years))
        else:
            # Fallback: calculate experience based on year pairs
            years, ans = extract_years(unique_exp_section)
            print(f"Year pairs: {years}, Total years: {ans}")
        print(unique_exp_section)
        print("="*100)

if __name__ == "__main__":
    main()