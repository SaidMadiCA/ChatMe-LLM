# Personal Chat API

A FastAPI application that allows users to chat with an AI assistant personalized with your background information.

## Features

- Chat interface using GPT-4o-mini
- FastAPI backend for API endpoints
- Gradio UI for interactive chat
- Tool system for recording user details and unknown questions
- Push notifications via Pushover

## Setup

1. Create the necessary files:
   ```
   mkdir -p me
   touch me/summary.txt
   ```

2. Add your LinkedIn PDF:
   - Save your LinkedIn profile as a PDF file
   - Place it in the `me/` folder as `linkedin.pdf`

3. Create a summary:
   - Edit `me/summary.txt` with a brief professional summary

4. Install dependencies:
   ```
   uv pip install -r requirements.txt
   ```

5. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key and Pushover credentials

## Running the application

```
uvicorn main:app --reload
```

Or with Gradio UI:

```
python main.py
```

## API Endpoints

- `GET /`: Welcome message
- `POST /chat`: Chat with the assistant
- `POST /record-details`: Record user contact information
- `POST /record-question`: Record unanswered questions

## Customization

Edit the `Me` class in `main.py` to customize:
- Your name
- System prompt
- Additional background information