import gradio as gr
import requests
import os

# --- Configuration ---
API_URL = "http://127.0.0.1:8000"

# --- API Client Functions ---


def upload_cvs_client(files):
    """Client function to call the /upload-cv/ endpoint."""
    if not files:
        return "Please upload at least one CV."

    file_list = [
        ("files", (os.path.basename(file.name), open(file.name, "rb")))
        for file in files
    ]

    try:
        response = requests.post(f"{API_URL}/upload-cv/", files=file_list)
        if response.status_code == 200:
            return "CVs uploaded successfully."
        else:
            return f"Error uploading CVs: {response.text}"
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"


def analyze_resumes_client(jd_file, top_n):
    """Client function to orchestrate the analysis process."""
    if not jd_file:
        return "Please upload a Job Description."

    # --- Step 1: Call the /scores endpoint to rank resumes and set the context ---
    try:
        print(f"Sending JD to /scores endpoint to get top {top_n} resumes...")
        files = {"file": (os.path.basename(jd_file.name), open(jd_file.name, "rb"))}
        scores_response = requests.post(f"{API_URL}/scores/?n={top_n}", files=files)

        if scores_response.status_code != 200:
            return f"Error getting scores: {scores_response.text}"
        print("Successfully got scores and set context on the backend.")

    except requests.exceptions.RequestException as e:
        return f"An error occurred while getting scores: {e}"

    # --- Step 2: Call the /query endpoint to generate the detailed summary ---
    try:
        print("Sending query to /query endpoint to generate summary...")
        query_payload = {
            "Query": "Generate a detailed analysis of the top candidates based on the provided job description."
        }
        summary_response = requests.post(
            f"{API_URL}/query/?n={top_n}", json=query_payload
        )

        if summary_response.status_code == 200:
            return summary_response.json().get("results", "No summary generated.")
        else:
            return f"Error generating summary: {summary_response.text}"
    except requests.exceptions.RequestException as e:
        return f"An error occurred while generating the summary: {e}"


# --- Gradio UI Definition ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🎯 Resume Ranking and Analysis System
        A tool to help you find the best candidates for a job.
        """
    )

    with gr.Tabs():
        with gr.TabItem("Step 1: Upload Resumes"):
            gr.Markdown("## Upload Candidate Resumes")
            gr.Markdown(
                "Upload multiple PDF or DOCX files at once. This will add the resumes to the database for analysis."
            )
            cv_files_input = gr.File(
                label="Upload CVs", file_count="multiple", file_types=[".pdf", ".docx"]
            )
            upload_button = gr.Button("Upload Resumes", variant="primary")
            upload_status_output = gr.Textbox(label="Status", interactive=False)

        with gr.TabItem("Step 2: Analyze Resumes"):
            gr.Markdown("## Analyze Resumes Against a Job Description")
            gr.Markdown(
                "Upload a Job Description, select the number of top candidates to analyze, and get a detailed report."
            )
            with gr.Row():
                jd_file_input = gr.File(
                    label="Upload Job Description", file_types=[".pdf", ".docx"]
                )
                top_n_slider = gr.Slider(
                    minimum=1,
                    maximum=20,
                    value=5,
                    step=1,
                    label="Number of resumes to analyze",
                )

            analyze_button = gr.Button("Analyze Resumes", variant="primary")

            gr.Markdown("--- ")
            gr.Markdown("## 📊 Analysis Report")
            analysis_output = gr.Markdown()

    # --- Event Handlers ---
    upload_button.click(
        fn=upload_cvs_client, inputs=[cv_files_input], outputs=[upload_status_output]
    )

    analyze_button.click(
        fn=analyze_resumes_client,
        inputs=[jd_file_input, top_n_slider],
        outputs=[analysis_output],
    )

if __name__ == "__main__":
    demo.launch(share=True)
