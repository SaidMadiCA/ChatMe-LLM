# Personal Chat API with RAG

A FastAPI application that allows users to chat with an AI assistant personalized with your background information. The application includes two versions: a basic chat version and an enhanced version with Retrieval Augmented Generation (RAG) capabilities.

## Features

### Core Features (Both Versions)
- Chat interface using GPT-4o-mini
- FastAPI backend for API endpoints
- Gradio UI for interactive chat
- Tool system for recording user details and unknown questions
- Push notifications via Pushover

### RAG Features (Enhanced Version)
- Document indexing and semantic search
- Automatic processing of PDF and text files
- Vector-based retrieval of relevant context
- Dedicated RAG query endpoint and client
- Gradio UI with RAG query tab

## Project Structure

```
.
├── main.py               # Basic chat application
├── main_rag.py           # Enhanced application with RAG
├── rag.py                # RAG implementation
├── client.py             # Basic chat client
├── rag_client.py         # RAG query client
├── setup_venv.sh         # Setup script for basic version
├── setup_rag_env.sh      # Setup script for RAG version
├── requirements.txt      # Dependencies for both versions
└── me/                   # Personal information and knowledge base
    ├── summary.txt       # Brief personal summary
    ├── linkedin.pdf      # LinkedIn profile as PDF
    └── knowledge/        # Additional knowledge documents
```

## Setup

### Prerequisites
- Python 3.9 or later
- OpenAI API key
- Pushover account (optional, for notifications)

### Basic Version Setup

1. Create the necessary files:
   ```bash
   mkdir -p me
   touch me/summary.txt
   ```

2. Add your LinkedIn PDF:
   - Save your LinkedIn profile as a PDF file
   - Place it in the `me/` folder as `linkedin.pdf`

3. Create a summary:
   - Edit `me/summary.txt` with a brief professional summary

4. Run the setup script:
   ```bash
   ./setup_venv.sh
   ```

5. Edit the `.env` file to add your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   PUSHOVER_TOKEN=your_pushover_token_here
   PUSHOVER_USER=your_pushover_user_key_here
   ```

### RAG Version Setup

1. Complete the same steps as the basic version setup

2. Create a knowledge directory for additional documents:
   ```bash
   mkdir -p me/knowledge
   ```

3. Add documents to your knowledge base:
   - Add PDF files to `me/knowledge/`
   - Add text files to `me/knowledge/`

4. Run the RAG setup script:
   ```bash
   ./setup_rag_env.sh
   ```

## Running the Application

### Basic Version

```bash
# Activate the virtual environment
source venv/bin/activate

# Run with Gradio UI
python main.py

# Or run with just FastAPI (without Gradio)
uvicorn main:app --reload
```

### RAG-Enhanced Version

```bash
# Activate the virtual environment
source venv/bin/activate

# Run with Gradio UI
python main_rag.py

# Or run with just FastAPI (without Gradio)
uvicorn main_rag:app --reload
```

## Using the Clients

### Basic Chat Client

```bash
# Activate the virtual environment
source venv/bin/activate

# Run the client
python client.py
```

### RAG Query Client

```bash
# Activate the virtual environment
source venv/bin/activate

# Run in interactive mode
python rag_client.py

# Or run a single query
python rag_client.py --query "What projects have you worked on?" --top_k 5
```

## API Endpoints

### Basic Version Endpoints
- `GET /`: Welcome message
- `POST /chat`: Chat with the assistant
- `POST /record-details`: Record user contact information
- `POST /record-question`: Record unanswered questions

### RAG Version Additional Endpoints
- `POST /rag/query`: Query the RAG system

## Customization

Edit the `Me` class in `main.py` or `main_rag.py` to customize:
- Your name
- System prompt
- Additional background information

For the RAG version, you can also customize:
- Embedding model in `rag.py`
- Chunk size and overlap for document processing
- Number of context chunks to retrieve per query