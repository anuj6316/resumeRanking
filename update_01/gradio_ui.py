import gradio as gr
import os
import tempfile
from typing import List, Tuple
from resume_db import upload_cv
import sections_extractor_and_storage as jd
from config import Config
from scores import calculate_resume_scores
from llm import ai_res
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader

config = Config()

# Global variables to store state
latest_jd_text = None
latest_resume_ids = []
filtered_cvs_list = []

def jd_text(file_path):
    """Extract text from JD file (PDF or DOCX)"""
    if file_path.endswith('.docx') or file_path.endswith('.doc'):
        loader = Docx2txtLoader(file_path)
    elif file_path.endswith('.pdf'):
        loader = PyMuPDFLoader(file_path)
    else:
        return "Unsupported file format"
    
    data = loader.load()
    text = ""
    for doc in data:
        text += doc.page_content + "\n\n"
    return text

def upload_jd_file(file) -> str:
    """Process uploaded JD file and return status"""
    global latest_jd_text, latest_resume_ids, filtered_cvs_list
    
    if file is None:
        return "No file uploaded"
    
    try:
        # Extract text from JD
        text = jd_text(file.name)
        
        # Classify JD and calculate scores
        result = jd.classify_jd(text)
        result_dict = result.dict()
        result_dict['jd_text'] = text
        
        # Calculate resume scores
        scores = calculate_resume_scores(result_dict)
        
        # Store globally
        latest_jd_text = text
        latest_resume_ids = list(scores.keys())[:10]  # Top 10 resumes
        
        # Update filtered CVs list for display
        filtered_cvs_list = [f"Resume ID: {rid}" for rid in latest_resume_ids]
        
        return f"✅ JD processed successfully! Found {len(latest_resume_ids)} matching resumes."
    
    except Exception as e:
        return f"❌ Error processing JD: {str(e)}"

def upload_cv_files(files) -> str:
    """Process uploaded CV files"""
    if not files:
        return "No files uploaded"
    
    results = []
    upload_dir = "uploaded_cvs"
    os.makedirs(upload_dir, exist_ok=True)
    
    try:
        for file in files:
            # Save file temporarily
            file_location = os.path.join(upload_dir, os.path.basename(file.name))
            
            # Copy file content
            with open(file.name, "rb") as src, open(file_location, "wb") as dst:
                dst.write(src.read())
            
            # Upload to database
            result = upload_cv(file_location)
            results.append(f"✅ {os.path.basename(file.name)}: {result}")
        
        return "\n".join(results)
    
    except Exception as e:
        return f"❌ Error uploading CVs: {str(e)}"

def chat_with_ai(message: str, history: List[dict]) -> Tuple[str, List[dict]]:
    """Handle chat with AI"""
    global latest_jd_text, latest_resume_ids
    
    if not latest_jd_text or not latest_resume_ids:
        response = "❌ Please upload a JD file first to start chatting about resumes."
    else:
        try:
            # Get AI response
            response = ai_res(message, latest_jd_text, latest_resume_ids[:5])
        except Exception as e:
            response = f"❌ Error getting AI response: {str(e)}"
    
    # Update history with new message format
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})
    return "", history

def get_filtered_cvs() -> str:
    """Return the list of filtered CVs"""
    global filtered_cvs_list
    
    if not filtered_cvs_list:
        return "No CVs filtered yet. Please upload a JD file first."
    
    return "\n".join([f"{i+1}. {cv}" for i, cv in enumerate(filtered_cvs_list)])

def create_ui():
    """Create the Gradio interface"""
    
    with gr.Blocks(title="Resume Ranking Chatbot", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🤖 Resume Ranking Chatbot")
        gr.Markdown("Upload JD and CVs, then chat with AI to analyze resumes!")
        
        with gr.Row():
            # Left Column - Upload Section
            with gr.Column(scale=1):
                gr.Markdown("## 📁 Upload Files")
                
                # JD Upload
                with gr.Group():
                    gr.Markdown("### 📋 Job Description")
                    jd_file = gr.File(
                        label="Upload JD (PDF/DOCX)",
                        file_types=[".pdf", ".docx", ".doc"],
                        type="filepath"
                    )
                    jd_upload_btn = gr.Button("🚀 Process JD", variant="primary")
                    jd_status = gr.Textbox(
                        label="JD Status",
                        interactive=False,
                        placeholder="Upload a JD file to get started..."
                    )
                
                # CV Upload
                with gr.Group():
                    gr.Markdown("### 📄 Resumes/CVs")
                    cv_files = gr.File(
                        label="Upload CVs (PDF/DOCX)",
                        file_count="multiple",
                        file_types=[".pdf", ".docx", ".doc"],
                        type="filepath"
                    )
                    cv_upload_btn = gr.Button("📤 Upload CVs", variant="secondary")
                    cv_status = gr.Textbox(
                        label="CV Upload Status",
                        interactive=False,
                        placeholder="Upload CV files to add to database..."
                    )
            
            # Middle Column - Chat Section
            with gr.Column(scale=2):
                gr.Markdown("## 💬 Chat with AI")
                
                chatbot = gr.Chatbot(
                    label="AI Assistant",
                    height=400,
                    placeholder="Upload a JD file first, then start asking questions about resumes!",
                    type="messages"
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="Your Message",
                        placeholder="Ask about resumes, rankings, or specific candidates...",
                        scale=4
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                
                gr.Markdown("### 💡 Example Questions:")
                gr.Markdown("""
                - "Which resume is most relevant for this position?"
                - "Compare the top 3 candidates"
                - "What skills are missing in the top candidates?"
                - "Rank resumes by experience level"
                """)
            
            # Right Column - Filtered CVs
            with gr.Column(scale=1):
                gr.Markdown("## 🎯 Filtered CVs")
                
                filtered_cvs_display = gr.Textbox(
                    label="Top Matching Resumes",
                    lines=15,
                    interactive=False,
                    placeholder="Process a JD file to see filtered resumes here..."
                )
                
                refresh_btn = gr.Button("🔄 Refresh List", variant="secondary")
        
        # Event handlers
        jd_upload_btn.click(
            fn=upload_jd_file,
            inputs=[jd_file],
            outputs=[jd_status]
        ).then(
            fn=get_filtered_cvs,
            outputs=[filtered_cvs_display]
        )
        
        msg.submit(
            fn=chat_with_ai,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot]
        )
        
        refresh_btn.click(
            fn=get_filtered_cvs,
            outputs=[filtered_cvs_display]
        )
    
    return demo

if __name__ == "__main__":
    # Create and launch the UI
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True
    )
