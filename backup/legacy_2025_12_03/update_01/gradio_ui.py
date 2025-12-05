import gradio as gr
import requests
import pandas as pd
import os

API_URL = "http://localhost:8000"


def upload_cvs(files):
    if not files:
        return "Please upload at least one CV."

    file_list = []
    for file in files:
        with open(file.name, "rb") as f:
            file_list.append(("files", (os.path.basename(file.name), f.read())))

    try:
        response = requests.post(f"{API_URL}/upload-cv/", files=file_list)
        if response.status_code == 200:
            return "CVs uploaded successfully."
        else:
            return f"Error: {response.text}"
    except Exception as e:
        return f"An error occurred: {str(e)}"


def get_scores(jd_file, top_n):
    if not jd_file:
        return "Please upload a Job Description.", None

    with open(jd_file.name, "rb") as f:
        files = {"file": (os.path.basename(jd_file.name), f.read())}

    try:
        response = requests.post(f"{API_URL}/scores/?n={top_n}", files=files)
        if response.status_code == 200:
            scores = response.json()
            df = pd.DataFrame.from_dict(scores, orient="index")
            df.index.name = "Resume ID"
            df = df.reset_index()
            df = df.rename(
                columns={"person_name": "Name", "overall_score": "Overall Score"}
            )
            return "Scores calculated successfully.", df
        else:
            return f"Error: {response.text}", None
    except Exception as e:
        return f"An error occurred: {str(e)}", None


def query_resumes(query, top_n):
    if not query:
        return "Please enter a query."

    try:
        response = requests.post(f"{API_URL}/query/?n={top_n}", json={"Query": query})
        if response.status_code == 200:
            return response.json().get("results")
        else:
            return f"Error: {response.text}"
    except Exception as e:
        return f"An error occurred: {str(e)}"


def chatbot_interaction(message, history):
    return query_resumes(message, 5)  # Default top_n to 5


with gr.Blocks() as demo:
    gr.Markdown("# Resume Ranking System for HR")

    with gr.Tab("Step 1: Upload Resumes (Optional)"):
        gr.Markdown(
            "## Upload candidate resumes here. You can upload multiple files at once."
        )
        cv_files = gr.File(label="Upload CVs", file_count="multiple")
        upload_button = gr.Button("Upload Resumes")
        upload_status = gr.Textbox(label="Status")
        upload_button.click(upload_cvs, inputs=cv_files, outputs=upload_status)

    with gr.Tab("Step 2: Score Resumes"):
        gr.Markdown("## Upload a Job Description to score the resumes.")
        jd_file = gr.File(label="Upload Job Description")
        top_n_slider = gr.Slider(
            minimum=1, maximum=20, value=5, step=1, label="Number of resumes to score"
        )
        score_button = gr.Button("Get Resume Scores")
        score_status = gr.Textbox(label="Status")
        score_results = gr.DataFrame(label="Ranked Resumes")
        score_button.click(
            get_scores,
            inputs=[jd_file, top_n_slider],
            outputs=[score_status, score_results],
        )

    with gr.Tab("Step 3: Chat with Resumes"):
        gr.Markdown("## Ask questions about the top-ranked resumes.")
        chatbot = gr.ChatInterface(chatbot_interaction)

if __name__ == "__main__":
    demo.launch()
