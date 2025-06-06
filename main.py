from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
import shutil
from pathlib import Path
from pypdf import PdfReader
import uvicorn
from typing import Optional, List, Dict, Any

# Import the Qdrant-based RAG system
from rag_qdrant import RAGSystem

# Load environment variables
load_dotenv(override=True)

app = FastAPI(
    title="Personal Chat API with RAG",
    description="API for chatting with me using GPT-4o-mini enhanced with RAG capabilities"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class UserDetails(BaseModel):
    email: EmailStr
    name: str = Field(default="Name not provided")
    notes: str = Field(default="not provided")

class Question(BaseModel):
    question: str

class ChatMessage(BaseModel):
    message: str
    history: list = []

class ChatResponse(BaseModel):
    response: str

class RAGQuery(BaseModel):
    query: str = Field(..., example="What projects have you worked on?")
    top_k: int = Field(default=3, ge=1, le=10, example=3)

class RAGSource(BaseModel):
    source: str
    content: str
    score: float
    chunk_id: Optional[int] = None

class RAGResponse(BaseModel):
    answer: str
    sources: List[RAGSource] = []
    
class FileUploadResponse(BaseModel):
    filename: str
    status: str
    message: str
    chunks_indexed: int

# Push notification function
def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )

# Tool functions
def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}

# Tool definitions
record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            },
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]

class Me:
    def __init__(self):
        self.openai = OpenAI()
        self.name = "Said Madi"
        self.rag = None
        try:
            reader = PdfReader("me/linkedin.pdf")
            self.linkedin = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    self.linkedin += text
                    
            with open("me/summary.txt", "r", encoding="utf-8") as f:
                self.summary = f.read()
                
            # Initialize RAG system with LinkedIn data
            self.initialize_rag()
        except FileNotFoundError as e:
            print(f"Warning: {e} - Some functionality may be limited")
            self.linkedin = "LinkedIn profile not available"
            self.summary = "Summary not available"
    
    def initialize_rag(self):
        """Initialize and populate the RAG system"""
        try:
            # Initialize RAG with Qdrant configuration from environment variables
            # Note: local_path is not used in client-server mode, but included for compatibility
            self.rag = RAGSystem(
                embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
                collection_name=os.getenv("QDRANT_COLLECTION", "knowledge_base"),
                local_path=os.getenv("QDRANT_LOCAL_PATH", "./qdrant_data")
            )
            
            # Get current document count to avoid re-adding documents
            doc_count = self.rag.get_document_count()
            if doc_count > 0:
                print(f"Found {doc_count} existing documents in Qdrant collection")
                return
                
            print("Initializing Qdrant with documents...")
        except Exception as e:
            print(f"Error initializing Qdrant: {e}")
            print("Falling back to in-memory RAG system")
            # Import the original RAG system as a fallback
            from rag import RAGSystem as InMemoryRAGSystem
            self.rag = InMemoryRAGSystem()
            print("Using in-memory RAG system instead")
        
        # Add summary and LinkedIn data
        self.rag.add_text(self.summary, {"source": "summary"})
        self.rag.add_text(self.linkedin, {"source": "linkedin"})
        
        # Add any additional documents in the knowledge directory
        knowledge_dir = "me/knowledge"
        if os.path.exists(knowledge_dir):
            for filename in os.listdir(knowledge_dir):
                file_path = os.path.join(knowledge_dir, filename)
                if filename.lower().endswith('.pdf'):
                    self.rag.add_pdf(file_path, {"source": filename})
                elif filename.lower().endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                        self.rag.add_text(text, {"source": filename})

    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results
    
    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt
    
    def chat(self, message, history=None):
        if history is None:
            history = []
            
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            if response.choices[0].finish_reason=="tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        return response.choices[0].message.content

# Initialize Me class
me = Me()

# Dependency for RAG system
def get_rag_system():
    if me.rag is None:
        me.initialize_rag()
    return me.rag

# API Endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    response = me.chat(chat_message.message, chat_message.history)
    return {"response": response}

@app.post("/rag/query", response_model=RAGResponse)
async def rag_query(query: RAGQuery, rag_system: RAGSystem = Depends(get_rag_system)):
    """
    Query the system using Retrieval Augmented Generation (RAG)
    """
    try:
        answer, sources = rag_system.query(query.query, top_k=query.top_k)
        return {"answer": answer, "sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing RAG query: {str(e)}")

@app.post("/record-details")
async def record_details_endpoint(user_details: UserDetails, background_tasks: BackgroundTasks):
    background_tasks.add_task(record_user_details, user_details.email, user_details.name, user_details.notes)
    return {"status": "success", "message": "User details recorded"}

@app.post("/record-question")
async def record_question_endpoint(question: Question, background_tasks: BackgroundTasks):
    background_tasks.add_task(record_unknown_question, question.question)
    return {"status": "success", "message": "Question recorded"}

@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...), custom_name: Optional[str] = Form(None)):
    """
    Upload a file to the knowledge base for RAG indexing
    """
    try:
        # Create knowledge directory if it doesn't exist
        knowledge_dir = Path("me/knowledge")
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        # Get the file extension
        file_extension = Path(file.filename).suffix.lower()
        
        # Check if file type is supported
        if file_extension not in ['.txt', '.pdf']:
            raise HTTPException(status_code=400, detail="Only .txt and .pdf files are supported")
        
        # Use custom name if provided, otherwise use original filename
        base_name = custom_name if custom_name else Path(file.filename).stem
        # Clean the filename to remove special characters
        base_name = ''.join(c for c in base_name if c.isalnum() or c in [' ', '.', '_', '-']).strip()
        
        # Generate final filename with the original extension
        final_filename = f"{base_name}{file_extension}"
        file_path = knowledge_dir / final_filename
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Add the file to the RAG system
        chunks_indexed = 0
        if file_extension == '.pdf':
            chunks_indexed = me.rag.add_pdf(str(file_path), {"source": final_filename})
        else:  # .txt
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                chunks_indexed = me.rag.add_text(text, {"source": final_filename})
        
        return {
            "filename": final_filename,
            "status": "success",
            "message": f"File uploaded and indexed successfully",
            "chunks_indexed": chunks_indexed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {me.name}'s chat API with RAG capabilities",
        "endpoints": {
            "chat": "/chat",
            "rag": "/rag/query",
            "upload": "/upload"
        }
    }

# For standalone execution with Gradio UI
if __name__ == "__main__":
    import gradio as gr
    
    # Define Gradio interface using FastAPI backend
    with gr.Blocks(title=f"Chat with {me.name}") as interface:
        with gr.Tab("Chat"):
            chatbot = gr.Chatbot()
            msg = gr.Textbox(label="Message")
            clear = gr.Button("Clear")
            
            def respond(message, chat_history):
                # Format history for API
                formatted_history = []
                if chat_history:
                    for user_msg, bot_msg in chat_history:
                        formatted_history.append({"role": "user", "content": user_msg})
                        formatted_history.append({"role": "assistant", "content": bot_msg})
                
                # Use the FastAPI endpoint instead of direct method call
                import requests
                response = requests.post(
                    "http://localhost:8000/chat",
                    json={"message": message, "history": formatted_history}
                )
                
                if response.status_code == 200:
                    bot_response = response.json()["response"]
                else:
                    bot_response = f"Error: Could not get response from API. Status code: {response.status_code}"
                
                # Add to chat history in Gradio format (list of pairs)
                chat_history.append((message, bot_response))
                
                return "", chat_history
            
            msg.submit(respond, [msg, chatbot], [msg, chatbot])
            clear.click(lambda: None, None, chatbot, queue=False)
        
        with gr.Tab("RAG Query"):
            query_input = gr.Textbox(label="Question")
            top_k = gr.Slider(minimum=1, maximum=10, value=3, step=1, label="Number of context chunks")
            query_button = gr.Button("Search")
            answer_output = gr.Textbox(label="Answer")
            sources_output = gr.JSON(label="Sources")
            
            def rag_search(query, k):
                # Use the FastAPI endpoint instead of direct method call
                import requests
                response = requests.post(
                    "http://localhost:8000/rag/query",
                    json={"query": query, "top_k": k}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["answer"], result["sources"]
                else:
                    return f"Error: Could not get response from API. Status code: {response.status_code}", []
            
            query_button.click(rag_search, [query_input, top_k], [answer_output, sources_output])
            
        with gr.Tab("Upload Document"):
            with gr.Column():
                file_upload = gr.File(label="Upload a document for the knowledge base", file_types=[".txt", ".pdf"])
                custom_name = gr.Textbox(label="Custom document name (optional)", placeholder="Leave blank to use original filename")
                upload_button = gr.Button("Upload and Index")
                upload_status = gr.Textbox(label="Status", interactive=False)
                upload_details = gr.JSON(label="Details", visible=False)
                
                def upload_document(file, custom_name):
                    if file is None:
                        return "Please select a file to upload", {}
                    
                    try:
                        import requests
                        import os
                        
                        # Create a form with the file and custom name
                        files = {'file': (os.path.basename(file.name), open(file.name, 'rb'), 'application/octet-stream')}
                        data = {}
                        if custom_name:
                            data['custom_name'] = custom_name
                        
                        # Send request to the upload endpoint
                        response = requests.post(
                            "http://localhost:8000/upload",
                            files=files,
                            data=data
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            status_message = f"Success: {result['filename']} uploaded and indexed with {result['chunks_indexed']} chunks"
                            return status_message, result
                        else:
                            return f"Error: {response.status_code} - {response.text}", {}
                    except Exception as e:
                        return f"Error: {str(e)}", {}
                
                upload_button.click(
                    upload_document, 
                    [file_upload, custom_name], 
                    [upload_status, upload_details]
                )
        
        # Launch Gradio with FastAPI backend
        # First start the FastAPI server in a separate thread
        import threading
        import time
        
        def start_fastapi():
            import uvicorn
            uvicorn.run(app, host="localhost", port=8000)
        
        # Start FastAPI server in a separate thread
        fastapi_thread = threading.Thread(target=start_fastapi, daemon=True)
        fastapi_thread.start()
        
        # Give FastAPI server a moment to start
        time.sleep(1)
        
        # Then launch Gradio on a different port
        interface.launch(server_name="0.0.0.0", server_port=8001, share=True)
    
    # If running without Gradio, use Uvicorn to start the FastAPI app
    # uvicorn.run(app, host="0.0.0.0", port=8000)