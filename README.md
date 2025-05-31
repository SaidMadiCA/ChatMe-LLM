# Personal Chat API with RAG

A sophisticated FastAPI application that creates a personalized AI assistant enhanced with Retrieval Augmented Generation (RAG) capabilities. This application allows you to create a digital representation of yourself that can answer questions based on your personal information, LinkedIn profile, and any additional knowledge documents.

## Architecture & Technical Details

### Core Components

1. **FastAPI Backend**
   - RESTful API with JSON-based communication
   - Swagger documentation at `/docs`
   - CORS-enabled for cross-origin requests
   - Type validation with Pydantic models

2. **RAG Implementation**
   - OpenAI embeddings for semantic search (`text-embedding-3-small`)
   - Document chunking with configurable size and overlap
   - PDF and text file processing
   - Cosine similarity scoring for relevant context retrieval
   - No external vector database required (in-memory storage)

3. **LLM Integration**
   - Uses OpenAI's GPT-4o-mini model
   - Function calling for tool usage
   - System prompt engineering for persona adoption
   - Contextual response generation

4. **Interactive UI**
   - Gradio-based interface with tabbed layout
   - Chat interface with message history
   - Dedicated RAG query interface
   - Source attribution display

5. **Clients**
   - Command-line chat client
   - RAG-specific query client with result formatting
   - Interactive and single-query modes

### API Endpoints

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|--------------|----------|
| `/` | GET | Welcome message | None | Basic info with available endpoints |
| `/chat` | POST | Chat with AI assistant | `ChatMessage` (message + history) | `ChatResponse` (AI response) |
| `/rag/query` | POST | Direct RAG query | `RAGQuery` (query + top_k) | `RAGResponse` (answer + sources) |
| `/record-details` | POST | Record user contact | `UserDetails` (email, name, notes) | Success message |
| `/record-question` | POST | Record unanswered questions | `Question` (question text) | Success message |

## Setup & Installation

### Prerequisites

- Python 3.9+ 
- OpenAI API key
- Personal information:
  - LinkedIn profile PDF
  - Brief summary text
  - (Optional) Additional knowledge documents

### Environment Setup

1. **Clone the repository or set up the project directory**

2. **Create necessary files and directories**
   ```bash
   mkdir -p me/knowledge
   touch me/summary.txt
   ```

3. **Add your personal information**
   - Save LinkedIn profile as PDF in `me/linkedin.pdf`
   - Write professional summary in `me/summary.txt`
   - Add any additional documents to `me/knowledge/` (PDF or TXT format)

4. **Run the setup script**
   ```bash
   chmod +x setup_env.sh  # Make executable if needed
   ./setup_env.sh
   ```
   This will:
   - Create a Python virtual environment
   - Install all dependencies
   - Set up the necessary directories
   - Create a template .env file

5. **Configure environment variables**
   Edit the `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   PUSHOVER_TOKEN=your_pushover_token_here  # Optional
   PUSHOVER_USER=your_pushover_user_key_here  # Optional
   ```

## Running the Application

### Starting the Server

There are two ways to run the application:

1. **Gradio UI Mode** (Recommended):
   ```bash
   # Activate the virtual environment
   source venv/bin/activate

   # Start the server with Gradio UI
   python main.py
   ```
   This launches both the FastAPI backend and the Gradio UI frontend on http://0.0.0.0:8000

2. **API-Only Mode**:
   ```bash
   # Activate the virtual environment
   source venv/bin/activate

   # Run with just FastAPI (no UI)
   uvicorn main:app --reload
   ```
   This launches only the FastAPI endpoints without the Gradio UI.

### Important Note on Running Modes

The application has different behavior depending on how you start it:

- **Gradio UI Mode (`python main.py`)**: 
  - Launches a Gradio interface at http://0.0.0.0:8000
  - The REST API endpoints are NOT directly accessible
  - RAG functionality is accessed through the Gradio UI or the modified RAG client

- **API-Only Mode (`uvicorn main:app --reload`)**: 
  - Launches only the REST API at http://localhost:8000
  - The Gradio UI is NOT available
  - All REST API endpoints are directly accessible at their documented URLs
  - Swagger documentation is available at http://localhost:8000/docs

### Using the Clients

#### Chat Client
For general conversation with your AI persona:

```bash
# Activate the virtual environment
source venv/bin/activate

# Run the chat client (works with both server modes)
python client.py
```

#### RAG Client
For direct knowledge base queries with source attribution:

```bash
# When server is in API-Only Mode (uvicorn main:app --reload)
python rag_client.py

# Note: rag_client.py is configured for API-Only Mode by default
# If you want to use it with Gradio UI Mode, edit rag_client.py to change:
# - URL from "http://localhost:8000/rag/query" to "http://0.0.0.0:8000/gradio_api/rag_search"
# - Payload parameter from "top_k" to "k"
# - Response parsing to handle the Gradio API response format

# Single query mode
python rag_client.py --query "What projects have you worked on?" --top_k 5
```

### Accessing the Web UI

- **Gradio UI**: http://0.0.0.0:8000 (when running `python main.py`)
  - **Chat Tab**: Interactive conversation with your AI persona
  - **RAG Query Tab**: Direct knowledge base queries with source attribution
- **FastAPI Swagger docs**: http://localhost:8000/docs (only when running `uvicorn main:app --reload`)

### Using the Gradio UI

The Gradio UI provides a user-friendly interface for interacting with the system:

1. **Chat Tab**:
   - Type your message in the text box and press Enter
   - View the conversation history in the chat window
   - Clear the conversation with the Clear button
   - The chat uses your personal information to provide context-aware responses

2. **RAG Query Tab**:
   - Enter your question in the Question field
   - Adjust the number of context chunks with the slider (1-10)
   - Click Search to get an answer
   - View the answer and the source documents that were used
   - Sources are displayed with their content and relevance score

## Technical Implementation Details

### RAG System

The RAG implementation follows these steps:

1. **Document Processing**
   - Documents are loaded from `me/linkedin.pdf`, `me/summary.txt`, and `me/knowledge/*`
   - Text is extracted from PDFs using PyPDF
   - Documents are chunked into smaller segments (default: 500 chars with 100 char overlap)
   - Sentence boundaries are preserved during chunking

2. **Embedding Generation**
   - Each chunk is embedded using OpenAI's text-embedding-3-small model
   - Embeddings are stored in memory along with document metadata

3. **Query Processing**
   - User query is embedded using the same model
   - Cosine similarity is calculated between query and all document chunks
   - Top k most relevant chunks are retrieved (default: k=3)

4. **Response Generation**
   - Retrieved chunks are combined as context
   - GPT-4o-mini generates a response based on the context and query
   - Both the response and source information are returned

### Me Class

The `Me` class manages:
- Personal information loading
- RAG system initialization
- System prompt construction
- Tool handling for recording user information
- Contextual chat functionality

### Data Flow

1. User sends query via client or UI
2. Server processes the query through FastAPI
3. If using `/chat` endpoint:
   - Query is processed with full persona context
   - Function calling may be triggered for tools
4. If using `/rag/query` endpoint:
   - RAG system retrieves relevant context
   - Response is generated based on context only
5. Response is returned to the client/UI

## Customization

### Personal Information
Edit the `Me` class in `main.py`:
```python
self.name = "Your Name"  # Change to your name
```

### System Prompt
Modify the `system_prompt` method in the `Me` class to change how the AI represents you.

### RAG Parameters
Adjust in `rag.py`:
```python
def __init__(self, 
             embedding_model: str = "text-embedding-3-small",  # Change embedding model
             chunk_size: int = 500,  # Adjust chunk size
             chunk_overlap: int = 100):  # Adjust overlap
```

### UI Customization
Modify the Gradio interface in `main.py` to add additional UI elements or change styling.

## Technical Limitations & Considerations

- **In-Memory Storage**: Document embeddings are stored in memory, which may not scale for very large knowledge bases
- **API Key Security**: Ensure your .env file is properly secured and not committed to version control
- **Rate Limiting**: Be mindful of OpenAI API usage and associated costs
- **Cold Start**: First query after server start may be slower due to embedding generation
- **Server Mode Differences**: The API endpoints behave differently depending on how you start the server

## Troubleshooting

- **Connection Errors**: Ensure the server is running before using clients
- **API Key Issues**: Check that your OpenAI API key is valid and has sufficient quota
- **File Not Found Errors**: Verify paths to your LinkedIn PDF and summary file
- **Dependency Problems**: Make sure all packages are installed with the correct versions
- **RAG Client Errors**: Verify that the client is configured correctly for your server mode
- **Chat UI Not Working**: If the chat UI doesn't work, try the following:
  - Ensure you're running the latest version of the code
  - Restart the server in Gradio UI mode (`python main.py`)
  - Clear your browser cache or try a different browser
  - Check browser console for any JavaScript errors

## Extension Ideas

- Add persistent vector storage using FAISS on disk or a database
- Implement authentication for the API
- Add document management endpoints for adding/removing knowledge files
- Create a web frontend beyond the Gradio UI
- Add support for more file formats beyond PDF and TXT