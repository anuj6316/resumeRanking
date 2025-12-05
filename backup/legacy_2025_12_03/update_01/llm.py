from langchain_community.vectorstores import Qdrant as QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from config import Config
from dotenv import load_dotenv

load_dotenv()
config = Config()

Template = """
You are very expert in resume screening based on the job description below.
{jd}
Please rate each candidate's resume on a scale of 1 to 10 based on their relevance to the job description.
The candidates' resumes are as follows:
{resumes}
Based on the given information, please provide best response with the user's query
{query}
"""

prompt = PromptTemplate(
    input_variables=["jd", "resumes", "query"],
    template=Template,
)

qdrant_client = QdrantClient(url="http://localhost:6333")
qdrant_store = QdrantVectorStore(
    client=qdrant_client, 
    collection_name=config.CV_COLLECTION, 
    embeddings=HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL)
)
def ai_res(query, jd, filter_resume_ids):
    """
    Retrieve relevant resumes and generate AI response.
    Handles None page_content gracefully by using custom search.
    """
    print("Retrieving resumes...")    
    try:
        # Initialize LLM
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
        
        # Format resumes for prompt
        resume_filter = Filter(
            must=[
                FieldCondition(
                    key="id",   # 👈 this must match your payload field name
                    match=MatchAny(any=filter_resume_ids)
                )
            ]
        )
        retriver = qdrant_store.as_retriever(search_kwargs={"filter": resume_filter}, k=3)
        # docs = retriver.search(query=query, k=3)
        
        # Create chain
        chain = (
            {
                'jd': lambda x: x['jd'],
                'resumes': lambda x: "\n\n".join(
                    doc.page_content for doc in retriver.invoke(x['query']) if getattr(doc, "page_content", None)
                ),
                'query': lambda x: x['query']
            }
            | prompt
            | llm
            | StrOutputParser()
        )
        
        # Invoke chain
        response = chain.invoke({
            "jd": jd, 
            "query": query,
        })
        
        return response
        
    except Exception as e:
        print(f"Error during LLM processing: {e}")
        import traceback
        traceback.print_exc()
        return f"An error occurred while processing: {str(e)}"


def clean_qdrant_collection():
    """
    Clean up documents with None content in Qdrant collection.
    Run this to permanently fix the data quality issue.
    """
    try:
        print("Scanning Qdrant collection for invalid documents...")
        
        # Scroll through all points
        points, next_offset = qdrant_client.scroll(
            collection_name=config.CV_COLLECTION,
            limit=1000,
            with_payload=True
        )
        
        # Find points with None or empty content
        invalid_ids = []
        content_key = qdrant_store.content_payload_key or "page_content"
        
        for point in points:
            content = point.payload.get(content_key)
            if content is None or (isinstance(content, str) and not content.strip()):
                invalid_ids.append(point.id)
                print(f"  Found invalid document: {point.id}")
        
        if invalid_ids:
            print(f"\nDeleting {len(invalid_ids)} invalid documents...")
            qdrant_client.delete(
                collection_name=config.RESUME_COLLECTION,
                points_selector=invalid_ids
            )
            print("✓ Cleanup complete!")
        else:
            print("✓ No invalid documents found. Collection is clean!")
        
        # Show collection stats
        collection_info = qdrant_client.get_collection(config.CV_COLLECTION)
        print(f"\nCollection stats:")
        print(f"  Total points: {collection_info.points_count}")
            
    except Exception as e:
        print(f"Error during cleanup: {e}")
        import traceback
        traceback.print_exc()


def main():
    # Uncomment to clean your Qdrant database first (recommended)
    print("="*80)
    print("STEP 1: Cleaning Qdrant Collection")
    print("="*80)
    # clean_qdrant_collection()
    print()
    
    filter_resume_ids = [
        'c902d79d-3d54-59db-bf0c-932b1e039aa1'
    ]
    
    jd = """
Job Title: Frontend Developer
Company: Levy, Carr and Rodriguez
Location: New Todd, El Salvador
Experience Required: 5+ years
Job Description:
We are looking for a talented Frontend Developer to join our team at Levy, Carr and Rodriguez. The
ideal candidate will have a strong background in software development and a passion for building
innovative solutions.
Key Responsibilities:
- Collaborate with cross-functional teams
- Automate deployment pipelines
- Implement machine learning models
- Conduct code reviews and testing
Required Skills:
- Node.js
- Docker
- TensorFlow
- CI/CD
- JavaScript
Preferred Hobbies / Personality Fit:
- Traveling
Why Join Us:
- Innovative and collaborative work culture
- Opportunities for growth and learning
- Competitive compensation and benefits
    """
    
    query = "Which resume is most relevant to developer position?"
    
    print("="*80)
    print("STEP 2: Processing Query")
    print("="*80)
    response = ai_res(query, jd, filter_resume_ids)
    print("\n" + "="*80)
    print("AI Response:")
    print("="*80)
    print(response)
    print("="*80)


if __name__ == "__main__":
    main()